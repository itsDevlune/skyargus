import hashlib
import io
import json

import pytest
from astropy.wcs import WCS
from django.test import Client
from PIL import Image

from apps.core.models import Artifact, Report, Sequence

pytestmark = pytest.mark.django_db


@pytest.fixture
def export_report(client, settings, tmp_path):
    """Synthetic colors isolate frame/annotation selection from archive availability."""
    settings.DATA_ROOT = tmp_path
    session = client.session
    session.save()
    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [10.5, 10.5]
    wcs.wcs.cdelt = [-0.001, 0.001]
    wcs.wcs.crval = [10, 20]
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    sequence = Sequence.objects.create(cache_key="export-regression", manifest={})
    frames = []
    for index, color in enumerate(["red", "blue"]):
        stream = io.BytesIO()
        Image.new("RGB", (20, 20), color).save(stream, format="PNG")
        raw = stream.getvalue()
        filename = f"frame-{index}.png"
        (tmp_path / filename).write_bytes(raw)
        artifact = Artifact.objects.create(
            sequence=sequence,
            filename=filename,
            sha256=hashlib.sha256(raw).hexdigest(),
            media_type="image/png",
            size=len(raw),
        )
        frames.append(
            {
                "id": f"test-{index}",
                "source": "Synthetic test fixture",
                "release": "test",
                "date": f"2025-01-0{index + 1}T00:00:00",
                "units": "test",
                "preview": {"id": str(artifact.id)},
            }
        )
    ra0, dec0 = wcs.pixel_to_world_values(4, 4)
    ra1, dec1 = wcs.pixel_to_world_values(14, 14)
    ra0, dec0, ra1, dec1 = map(float, (ra0, dec0, ra1, dec1))
    manifest = {
        "data_mode": "simulated",
        "frames": frames,
        "geometry": {"mode": "celestial", "width": 20, "height": 20, "wcs": wcs.to_header().tostring()},
    }
    return Report.objects.create(
        owner=session.session_key,
        sequence=sequence,
        snapshot={
            "sequence": manifest,
            "settings": {"index": 1},
            "candidates": [{"frame": 0, "ra": ra0, "dec": dec0}, {"frame": 1, "ra": ra1, "dec": dec1}],
        },
    )


def get_image(client, report, kind):
    response = client.get(f"/api/v1/reports/{report.id}/exports/{kind}")
    assert response.status_code == 200
    return Image.open(io.BytesIO(response.content)).convert("RGB")


def post_json(client, url, payload):
    return client.post(
        url,
        json.dumps(payload),
        content_type="application/json",
    )


def test_png_exports_saved_selected_frame_and_only_its_annotations(client, export_report):
    image = get_image(client, export_report, "png")
    assert image.getpixel((1, 1)) == (0, 0, 255)  # Selected frame 1, not red frame 0.
    # Frame 1 annotation centered at (58,22), radius 5; tolerate WCS float rounding.
    marker_pixels = [(x, y) for y in range(80) for x in range(80) if image.getpixel((x, y)) == (142, 184, 255)]
    assert marker_pixels
    assert all(50 <= x <= 65 and 14 <= y <= 29 for x, y in marker_pixels)
    # The frame-0 marker at (18,62) must not leak into the selected-frame export.
    assert image.getpixel((18, 62)) == (0, 0, 255)
    assert image.info["FrameIndex"] == "1"
    assert image.info["ObservationID"] == "test-1"
    assert image.info["Observed"] == "2025-01-02T00:00:00"


def test_gif_still_exports_all_frames_in_order(client, export_report):
    response = client.get(f"/api/v1/reports/{export_report.id}/exports/gif")
    assert response.status_code == 200
    image = Image.open(io.BytesIO(response.content))
    assert image.n_frames == 2
    assert image.convert("RGB").getpixel((1, 1)) == (255, 0, 0)
    image.seek(1)
    assert image.convert("RGB").getpixel((1, 1)) == (0, 0, 255)


@pytest.mark.parametrize("index", [-1, 2, 1.5, "bad", True])
def test_png_invalid_saved_selection_is_explicit(client, export_report, index):
    export_report.snapshot["settings"]["index"] = index
    export_report.save()
    assert client.get(f"/api/v1/reports/{export_report.id}/exports/png").status_code == 422


def test_old_report_without_selection_defaults_to_first_frame(client, export_report):
    export_report.snapshot.pop("settings")
    export_report.save()
    assert get_image(client, export_report, "png").getpixel((1, 1)) == (255, 0, 0)


def test_png_remains_private_to_report_owner(export_report):
    assert Client().get(f"/api/v1/reports/{export_report.id}/exports/png").status_code == 404


def test_export_rejects_unsupported_format(client):
    sequence = Sequence.objects.create(
        cache_key="export-unsupported-format",
        manifest={
            "frames": [],
            "warnings": [],
            "geometry": {"mode": "celestial"},
        },
    )
    report = post_json(
        client,
        "/api/v1/reports",
        {"sequence": str(sequence.id), "title": "test"},
    ).json()

    response = client.get(f"/api/v1/reports/{report['id']}/exports/webp")

    assert response.status_code == 400


def test_export_rejects_empty_sequence(client):
    sequence = Sequence.objects.create(
        cache_key="export-empty-sequence",
        manifest={
            "frames": [],
            "warnings": [],
            "geometry": {"mode": "celestial"},
        },
    )
    report = post_json(
        client,
        "/api/v1/reports",
        {"sequence": str(sequence.id), "title": "test"},
    ).json()

    response = client.get(f"/api/v1/reports/{report['id']}/exports/png")

    assert response.status_code == 422


