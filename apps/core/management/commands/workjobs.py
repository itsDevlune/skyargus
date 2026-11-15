import time
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import Job
from apps.core.tasks import publish, run_job


class Command(BaseCommand):
    help = "Isolated local database worker, or production dispatch reconciliation with --publish"

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--publish", action="store_true")
        parser.add_argument("--recover", action="store_true")

    def handle(self, *args, **opts):
        self.active_job = None
        try:
            self.run_loop(**opts)
        except KeyboardInterrupt:
            if self.active_job:
                Job.objects.filter(pk=self.active_job, state='running').update(
                    state='queued', stage='Worker stopped; saved progress retained for restart', updated=timezone.now()
                )
            self.stdout.write('Worker stopped. Saved observations and verified transfer chunks are preserved.')

    def run_loop(self, **opts):
        if opts["recover"]:
            Job.objects.filter(state="running", updated__lt=timezone.now() - timedelta(minutes=10)).update(
                state="queued", stage="Recovered expired worker lease"
            )
            Job.objects.filter(state="cancel_requested", updated__lt=timezone.now() - timedelta(minutes=10)).update(
                state="cancelled"
            )
        while True:
            if opts["recover"]:
                Job.objects.filter(state="running", updated__lt=timezone.now() - timedelta(minutes=10)).update(
                    state="queued", stage="Recovered expired worker lease"
                )
            for job in Job.objects.filter(state="queued").order_by("created")[:10]:
                if opts["publish"]:
                    if job.dispatch.published is None or job.dispatch.published < timezone.now() - timedelta(minutes=1):
                        publish(job.id)
                else:
                    self.active_job = job.id
                    run_job(str(job.id))
                    self.active_job = None
            if opts["once"]:
                return
            time.sleep(2)
