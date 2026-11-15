from unittest.mock import patch

import pytest
from django.core.management import call_command

from apps.core.models import Job
from apps.core.tasks import run_job
from science.coordinates import region


@pytest.mark.django_db
def test_cube_timeout_requeues_with_saved_progress():
    job = Job.objects.create(owner='test', kind='cube', selection=region({'ra': 10, 'dec': 20}))
    with patch('apps.core.cube_download.download_cube', side_effect=TimeoutError('transfer deadline')), patch('apps.core.tasks.publish') as publish:
        run_job(str(job.id))
    job.refresh_from_db()
    assert job.state == 'queued'
    assert job.attempts == 1
    assert 'verified chunks' in job.stage
    publish.assert_called_once_with(job.id)


@pytest.mark.django_db
def test_cube_timeout_stops_after_four_attempts():
    job = Job.objects.create(owner='test', kind='cube', attempts=3, selection=region({'ra': 10, 'dec': 20}))
    with patch('apps.core.cube_download.download_cube', side_effect=TimeoutError('transfer deadline')), patch('apps.core.tasks.publish') as publish:
        run_job(str(job.id))
    job.refresh_from_db()
    assert job.state == 'failed'
    assert job.attempts == 4
    assert 'Resume cube download' in job.error['message']
    publish.assert_not_called()


@pytest.mark.django_db
def test_worker_ctrl_c_preserves_and_requeues_active_job():
    job = Job.objects.create(owner='test', kind='cube', selection={})
    def interrupted(job_id):
        Job.objects.filter(pk=job_id).update(state='running')
        raise KeyboardInterrupt
    with patch('apps.core.management.commands.workjobs.run_job', side_effect=interrupted):
        call_command('workjobs', once=True)
    job.refresh_from_db()
    assert job.state == 'queued'
    assert 'progress retained' in job.stage
