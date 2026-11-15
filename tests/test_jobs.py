import hashlib
from datetime import timedelta
from pathlib import Path

import pytest
import requests
from django.core.management import call_command
from django.utils import timezone

from apps.core.models import Artifact, Job, Sequence
from apps.core.tasks import run_job
from science.coordinates import region

pytestmark = pytest.mark.django_db(transaction=True)


def fixture_inputs(monkeypatch, settings, tmp_path):
    settings.DATA_ROOT = tmp_path
    raw = (Path(__file__).parent / "fixtures/real/spherex-dr1-cutout.fits").read_bytes()
    row = {
        "id": "2025W33_2C_0321_1",
        "url": "https://irsa.ipac.caltech.edu/fixture.fits",
        "source": "SPHEREx",
        "release": "dr1",
        "mjd": 60902.8647,
        "end_mjd": 60902.8660,
    }
    monkeypatch.setattr("apps.core.tasks.discovery", lambda s: ([row.copy()], {"returned_metadata": 1}))
    monkeypatch.setattr("apps.core.tasks.get", lambda *args, **kwargs: raw)
    return raw


def test_second_fetch_reprojects_cached_native_inputs_during_archive_outage(monkeypatch, settings, tmp_path):
    raw = fixture_inputs(monkeypatch, settings, tmp_path)
    old = region({"ra": 269.452075, "dec": 4.693391, "detector": 3})
    old["processing"] = "older-processing-key"
    first = Job.objects.create(owner="test", selection=old)
    run_job(str(first.id))
    first.refresh_from_db()
    assert first.state == "completed"
    previous = Sequence.objects.get(pk=first.result["sequence"])

    response = requests.Response()
    response.status_code = 502

    def unavailable(*args, **kwargs):
        raise requests.HTTPError(response=response)

    monkeypatch.setattr("apps.core.tasks.discovery", unavailable)
    monkeypatch.setattr(
        "apps.core.tasks.get", lambda *args, **kwargs: pytest.fail("Must reuse native FITS without refetching")
    )
    selection = region({"ra": 269.453075, "dec": 4.693391, "detector": 3})
    second = Job.objects.create(owner="test", selection=selection)
    run_job(str(second.id))
    second.refresh_from_db()
    assert second.state == "partial"
    recovered = Sequence.objects.get(pk=second.result["sequence"])
    assert recovered.id != previous.id
    assert recovered.manifest["discovery"]["archive_search_succeeded"] is False
    assert recovered.manifest["geometry"]["crval"] == [selection["ra"], selection["dec"]]
    assert recovered.manifest["metrics"]["network_download_bytes"] == 0
    frame = recovered.manifest["frames"][0]
    assert frame["cutout_reused"] is True
    assert frame["original"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert "incomplete" in recovered.manifest["warnings"][0]


@pytest.mark.parametrize(
    "change",
    [
        {"ra": 0, "dec": 0},
        {"detector": 1},
        {"release": "qr3"},
        {"start": "2026-01-01"},
        {"end": "2024-01-01"},
    ],
)
def test_cache_recovery_respects_actual_footprint_release_detector_and_dates(monkeypatch, settings, tmp_path, change):
    from apps.core.cached_observations import discover_cached

    fixture_inputs(monkeypatch, settings, tmp_path)
    selected = {"ra": 269.452075, "dec": 4.693391, "detector": 3}
    first = Job.objects.create(owner="test", selection=region(selected))
    run_job(str(first.id))
    assert discover_cached(region({**selected, **change}), requests.ConnectionError("controlled outage")) is None


def test_cache_recovery_verifies_native_input_hash(monkeypatch, settings, tmp_path):
    from apps.core.cached_observations import discover_cached, read_cached_original

    fixture_inputs(monkeypatch, settings, tmp_path)
    selected = region({"ra": 269.452075, "dec": 4.693391, "detector": 3})
    first = Job.objects.create(owner="test", selection=selected)
    run_job(str(first.id))
    rows, _ = discover_cached(selected, requests.ConnectionError("controlled outage"))
    artifact = Artifact.objects.get(pk=rows[0]["cached_original_id"])
    (tmp_path / artifact.filename).write_bytes(b"corrupt input")
    with pytest.raises(ValueError, match="checksum mismatch"):
        read_cached_original(rows[0])


@pytest.mark.parametrize("offset, cutout_failure", [(0.001, False), (0.05, True)])
def test_live_metadata_reuses_saved_native_cutouts_when_appropriate(
    monkeypatch, settings, tmp_path, offset, cutout_failure
):
    fixture_inputs(monkeypatch, settings, tmp_path)
    first = Job.objects.create(owner="test", selection=region({"ra": 269.452075, "dec": 4.693391, "detector": 3}))
    run_job(str(first.id))

    def fetch(*args, **kwargs):
        if cutout_failure:
            raise requests.ConnectionError("Controlled cutout outage after metadata success")
        pytest.fail("Fully covered cached native input must not download again")

    monkeypatch.setattr("apps.core.tasks.get", fetch)
    second = Job.objects.create(
        owner="test", selection=region({"ra": 269.452075, "dec": 4.693391 + offset, "detector": 3})
    )
    run_job(str(second.id))
    second.refresh_from_db()
    assert second.state == ("partial" if cutout_failure else "completed")
    manifest = Sequence.objects.get(pk=second.result["sequence"]).manifest
    assert len(manifest["frames"]) == 1
    assert manifest["frames"][0]["cutout_reused"] is True
    assert manifest["metrics"]["network_download_bytes"] == 0
    if cutout_failure:
        assert manifest["discovery"]["cached_cutout_recovery"] is True
        assert manifest["frames"][0]["coverage_fraction"] < 1


def test_real_fixture_processing_idempotence_and_atomic_artifacts(monkeypatch, settings, tmp_path):
    raw = fixture_inputs(monkeypatch, settings, tmp_path)
    job = Job.objects.create(owner="test", selection=region({"ra": 269.452075, "dec": 4.693391, "detector": 3}))
    run_job(str(job.id))
    job.refresh_from_db()
    assert job.state == "completed"
    assert Sequence.objects.count() == 1
    seq = Sequence.objects.get(pk=job.result["sequence"])
    assert seq.manifest["data_mode"] == "real"
    assert seq.manifest["frames"][0]["original"]["sha256"] == hashlib.sha256(raw).hexdigest()
    for a in Artifact.objects.all():
        assert hashlib.sha256((tmp_path / a.filename).read_bytes()).hexdigest() == a.sha256
    run_job(str(job.id))
    assert Artifact.objects.count() == 3
    assert not list(tmp_path.glob("*.tmp"))


def test_cancel_during_download_preserves_stage_boundary(monkeypatch, settings, tmp_path):
    raw = fixture_inputs(monkeypatch, settings, tmp_path)
    job = Job.objects.create(owner="test", selection=region({"ra": 269.452075, "dec": 4.693391, "detector": 3}))

    def cancel(*args, **kwargs):
        Job.objects.filter(pk=job.id).update(state="cancel_requested")
        return raw

    monkeypatch.setattr("apps.core.tasks.get", cancel)
    run_job(str(job.id))
    job.refresh_from_db()
    assert job.state == "cancelled"
    assert not Sequence.objects.exists()


def test_upstream_outage_is_recorded_without_fake_frame(monkeypatch, settings, tmp_path):
    fixture_inputs(monkeypatch, settings, tmp_path)

    def fail(*args, **kwargs):
        raise TimeoutError("offline fixture outage")

    monkeypatch.setattr("apps.core.tasks.get", fail)
    job = Job.objects.create(owner="test", selection=region({"ra": 269.452075, "dec": 4.693391, "detector": 3}))
    run_job(str(job.id))
    job.refresh_from_db()
    seq = Sequence.objects.get(pk=job.result["sequence"])
    assert job.state == "partial"
    assert seq.manifest["frames"] == []
    assert seq.manifest["excluded"][0]["code"] == "archive_connection_failed"
    assert seq.manifest["excluded"][0]["retryable"] is True
    assert "http" not in seq.manifest["excluded"][0]["reason"]


def test_recovered_worker_attempt_cannot_overwrite_newer_result(monkeypatch):
    job = Job.objects.create(
        owner="test",
        kind="motion",
        selection={"points": [], "position_error_arcsec": 1.0},
    )
    calls = 0

    def fit_motion(*args):
        nonlocal calls
        calls += 1
        if calls == 1:
            Job.objects.filter(pk=job.id).update(updated=timezone.now() - timedelta(minutes=11))
            call_command("workjobs", once=True, recover=True)
        return {"attempt": calls}

    monkeypatch.setattr("science.motion.fit_motion", fit_motion)
    run_job(str(job.id))

    job.refresh_from_db()
    assert calls == 2
    assert job.attempts == 2
    assert job.state == "completed"
    assert job.result == {"attempt": 2}
