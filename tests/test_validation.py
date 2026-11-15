"""Regression tests for fixed validation defects (AUD-05 through AUD-08)."""

import json

import pytest

pytestmark = pytest.mark.django_db


def post(c, url, payload):
    return c.post(url, json.dumps(payload), content_type="application/json")


# ---------------------------------------------------------------------------
# AUD-05: sexagesimal RA 24:00:00 should be rejected
# ---------------------------------------------------------------------------
def test_sexagesimal_24h_rejected():
    from science.coordinates import region

    with pytest.raises(ValueError):
        region({"ra": "24:00:00", "dec": "0:00:00", "unit": "hourangle"})


def test_sexagesimal_23h59_accepted():
    from science.coordinates import region

    s = region({"ra": "23:59:59.999", "dec": "0:00:00", "unit": "hourangle"})
    assert s["ra"] == pytest.approx(360.0, abs=0.01)


def test_sexagesimal_negative_hour_rejected():
    from science.coordinates import region

    with pytest.raises((ValueError, Exception)):
        region({"ra": "-1:00:00", "dec": "0:00:00", "unit": "hourangle"})


# ---------------------------------------------------------------------------
# AUD-08: fractional detector should be rejected
# ---------------------------------------------------------------------------
def test_fractional_detector_rejected():
    from science.coordinates import region

    with pytest.raises((ValueError, TypeError)):
        region({"ra": 10, "dec": 10, "detector": 3.9})


def test_detector_string_float_rejected():
    from science.coordinates import region

    with pytest.raises((ValueError, TypeError)):
        region({"ra": 10, "dec": 10, "detector": "3.9"})


def test_detector_out_of_range_rejected():
    from science.coordinates import region

    with pytest.raises(ValueError):
        region({"ra": 10, "dec": 10, "detector": 7})
    with pytest.raises(ValueError):
        region({"ra": 10, "dec": 10, "detector": 0})


# ---------------------------------------------------------------------------
# AUD-06: non-UUID sequence in report/candidate → should be 400, not 500
# ---------------------------------------------------------------------------
def test_report_invalid_uuid_returns_client_error(client):
    r = post(client, "/api/v1/reports", {"sequence": "not-a-uuid", "title": "t"})
    assert r.status_code in (400, 404), f"Got {r.status_code}, expected 400 or 404"


def test_candidate_invalid_uuid_returns_client_error(client):
    data = {
        "sequence": "not-a-uuid",
        "frame": 0,
        "ra": 1,
        "dec": 2,
        "classification": "unsure",
    }
    r = post(client, "/api/v1/candidates", data)
    assert r.status_code in (400, 404), f"Got {r.status_code}, expected 400 or 404"


# ---------------------------------------------------------------------------
# AUD-07: candidate outside footprint should be rejected
# ---------------------------------------------------------------------------
def test_candidate_outside_footprint_rejected(client, sequence_with_frames):
    data = {
        "sequence": str(sequence_with_frames.id),
        "frame": 0,
        "ra": 0,
        "dec": 0,
        "classification": "unsure",
    }
    r = post(client, "/api/v1/candidates", data)
    # RA=0,Dec=0 is far outside a 6×6′ field at RA=269,Dec=4 — should be rejected
    assert r.status_code == 400, f"Out-of-footprint mark should be rejected, got {r.status_code}"


# ---------------------------------------------------------------------------
# Additional validation tests (not AUD-specific)
# ---------------------------------------------------------------------------
def test_empty_body_returns_400(client):
    r = client.post("/api/v1/searches", b"", content_type="application/json")
    # Empty body parses as {} which is missing ra/dec → 400
    assert r.status_code == 400


def test_non_json_body_returns_400(client):
    r = client.post("/api/v1/searches", b"not json", content_type="application/json")
    assert r.status_code == 400


def test_array_body_returns_400(client):
    r = client.post("/api/v1/searches", b"[1,2,3]", content_type="application/json")
    assert r.status_code == 400


def test_classification_enum_validated(client, sequence_with_frames):
    data = {
        "sequence": str(sequence_with_frames.id),
        "frame": 0,
        "ra": 269.452,
        "dec": 4.693,
        "classification": "definitely_aliens",
    }
    r = post(client, "/api/v1/candidates", data)
    assert r.status_code == 400


def test_note_length_limit(client, sequence_with_frames):
    data = {
        "sequence": str(sequence_with_frames.id),
        "frame": 0,
        "ra": 269.452,
        "dec": 4.693,
        "classification": "unsure",
        "note": "x" * 5000,
    }
    r = post(client, "/api/v1/candidates", data)
    assert r.status_code == 400


def test_frame_index_out_of_range_rejected(client, sequence_with_frames):
    data = {
        "sequence": str(sequence_with_frames.id),
        "frame": 99,
        "ra": 269.452,
        "dec": 4.693,
        "classification": "unsure",
    }
    r = post(client, "/api/v1/candidates", data)
    assert r.status_code == 400


def test_negative_frame_index_rejected(client, sequence_with_frames):
    data = {
        "sequence": str(sequence_with_frames.id),
        "frame": -1,
        "ra": 269.452,
        "dec": 4.693,
        "classification": "unsure",
    }
    r = post(client, "/api/v1/candidates", data)
    assert r.status_code == 400


def test_date_range_reversed_rejected():
    from science.coordinates import region

    with pytest.raises(ValueError):
        region({"ra": 10, "dec": 10, "start": "2025-12-01", "end": "2025-01-01"})


def test_fov_too_large_rejected():
    from science.coordinates import region

    with pytest.raises(ValueError):
        region({"ra": 10, "dec": 10, "width": 100, "height": 100})


def test_fov_too_small_rejected():
    from science.coordinates import region

    with pytest.raises(ValueError):
        region({"ra": 10, "dec": 10, "width": 0.5, "height": 0.5})


def test_invalid_source_rejected():
    from science.coordinates import region

    with pytest.raises(ValueError):
        region({"ra": 10, "dec": 10, "source": "hubble"})


def test_invalid_release_rejected():
    from science.coordinates import region

    with pytest.raises(ValueError):
        region({"ra": 10, "dec": 10, "release": "dr99"})


def test_resolution_empty_name_rejected(client):
    r = post(client, "/api/v1/resolve", {"name": ""})
    assert r.status_code == 400


def test_resolution_overlong_name_rejected(client):
    r = post(client, "/api/v1/resolve", {"name": "x" * 200})
    assert r.status_code == 400
