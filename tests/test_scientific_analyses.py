import uuid
from pathlib import Path

import pytest

from apps.core.models import Job, Sequence
from apps.core.tasks import run_job
from science.analysis import compute_epoch_stack, extract_source_spectrum
from science.coordinates import region

pytestmark = pytest.mark.django_db(transaction=True)


def setup_test_sequence(monkeypatch, settings, tmp_path):
    settings.DATA_ROOT = tmp_path
    raw = (Path(__file__).parent / "fixtures/real/spherex-dr1-cutout.fits").read_bytes()
    rows = [
        {
            "id": f"2025W33_2C_0321_{i}",
            "url": f"https://irsa.ipac.caltech.edu/fixture_{i}.fits",
            "source": "SPHEREx",
            "release": "dr1",
            "mjd": 60902.8647 + i * 0.01,
            "end_mjd": 60902.8660 + i * 0.01,
        }
        for i in range(1, 4)
    ]
    monkeypatch.setattr("apps.core.tasks.discovery", lambda s: (rows, {"returned_metadata": len(rows)}))
    monkeypatch.setattr("apps.core.tasks.get", lambda *args, **kwargs: raw)

    job = Job.objects.create(owner="test", selection=region({"ra": 269.452075, "dec": 4.693391, "detector": 3}))
    run_job(str(job.id))
    job.refresh_from_db()
    assert job.state == "completed"
    return Sequence.objects.get(pk=job.result["sequence"])


def test_spectrum_analysis_job(client, monkeypatch, settings, tmp_path):
    seq = setup_test_sequence(monkeypatch, settings, tmp_path)
    resp = client.post(
        "/api/v1/analyses",
        {
            "method": "spectrum",
            "sequence": str(seq.id),
            "ra": 269.452075,
            "dec": 4.693391,
            "aperture_radius_pix": 3.0,
        },
        content_type="application/json",
    )
    assert resp.status_code == 202
    job_id = resp.json()["job"]

    run_job(job_id)

    job = Job.objects.get(id=job_id)
    assert job.state == "completed"
    assert job.result["measurement_count"] == 3
    first = job.result["measurements"][0]
    assert "wavelength_um" in first
    assert "flux_mjy" in first
    assert "flux_err_mjy" in first
    assert "abmag" in first


def test_difference_analysis_job(client, monkeypatch, settings, tmp_path):
    seq = setup_test_sequence(monkeypatch, settings, tmp_path)
    resp = client.post(
        "/api/v1/analyses",
        {
            "method": "difference",
            "sequence": str(seq.id),
            "frame_a": 0,
            "frame_b": 1,
        },
        content_type="application/json",
    )
    assert resp.status_code == 202
    job_id = resp.json()["job"]

    run_job(job_id)

    job = Job.objects.get(id=job_id)
    assert job.state == "completed"
    assert job.result["valid_pixel_count"] > 1000
    assert job.result["bandpass_comparison"]["status"] == "overlapping_display_bandpasses"
    assert job.result["response_comparability"] == "not_assessed"
    assert "preview" in job.result
    assert job.result["preview"]["type"] == "image/png"


def test_epoch_stack_analysis_job(client, monkeypatch, settings, tmp_path):
    seq = setup_test_sequence(monkeypatch, settings, tmp_path)
    resp = client.post(
        "/api/v1/analyses",
        {
            "method": "stack",
            "sequence": str(seq.id),
            "frames": [0, 1],
        },
        content_type="application/json",
    )
    assert resp.status_code == 202
    job_id = resp.json()["job"]

    run_job(job_id)

    job = Job.objects.get(id=job_id)
    assert job.state == "completed"
    assert job.result["contributor_count"] == 2
    assert job.result["bandpass_comparison"]["status"] == "overlapping_display_bandpasses"
    assert job.result["response_comparability"] == "not_assessed"
    assert "preview" in job.result
    assert "fits" in job.result
    assert job.result["fits"]["type"] == "application/fits"


def test_composite_analysis_job(client, monkeypatch, settings, tmp_path):
    seq = setup_test_sequence(monkeypatch, settings, tmp_path)
    resp = client.post(
        "/api/v1/analyses",
        {
            "method": "composite",
            "sequence": str(seq.id),
            "red": 0,
            "green": 1,
            "blue": 2,
        },
        content_type="application/json",
    )
    assert resp.status_code == 202
    job_id = resp.json()["job"]

    run_job(job_id)

    job = Job.objects.get(id=job_id)
    assert job.state == "completed"
    assert "preview" in job.result
    assert job.result["preview"]["type"] == "image/png"
    assert "mapping" in job.result
    assert "red" in job.result["mapping"]
    assert job.result["response_comparability"] == "not_assessed"
    assert "visualization only" in job.result["warning"]


@pytest.mark.parametrize(
    "indices",
    [
        [],
        [0, 0],
        [0, 3],
        [0, -1],
        [0, 1.5],
        [0, True],
    ],
)
def test_epoch_stack_rejects_invalid_or_duplicate_frame_indices(indices, tmp_path):
    manifest = {
        "selection": {"ra": 10, "dec": 10, "width": 1, "height": 1},
        "frames": [{}, {}, {}],
    }

    with pytest.raises(ValueError):
        compute_epoch_stack(manifest, indices, tmp_path)


@pytest.mark.parametrize(
    "wavelengths",
    [
        ([1.0, 0.1], [2.0, 0.1]),
        ([1.0, 0.1], None),
    ],
)
def test_epoch_stack_rejects_disjoint_or_unassessed_bandpasses(wavelengths, tmp_path):
    manifest = {
        "selection": {"ra": 10, "dec": 10, "width": 1, "height": 1},
        "frames": [{"wavelength": wavelengths[0]}, {"wavelength": wavelengths[1]}],
    }

    with pytest.raises(ValueError, match="bandpass"):
        compute_epoch_stack(manifest, [0, 1], tmp_path)


def test_spectrum_fails_explicitly_when_original_artifact_is_missing(tmp_path):
    manifest = {
        "frames": [
            {
                "original": {"id": str(uuid.uuid4())},
            }
        ]
    }

    with pytest.raises(ValueError, match="artifact.*missing"):
        extract_source_spectrum(manifest, 10, 10, tmp_path)
