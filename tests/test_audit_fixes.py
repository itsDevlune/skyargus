import json

import pytest
import requests

from apps.core.errors import archive_error
from apps.core.models import Sequence
from science.coordinates import region
from science.imaging import grid


@pytest.mark.parametrize("ra", ["24:00:00", "24h00m00s", 24, -1])
def test_hourangle_boundaries(ra):
    with pytest.raises(ValueError):
        region({"ra": ra, "dec": 0, "unit": "hourangle"})


@pytest.mark.parametrize("detector", [3.9, True, "2.5"])
def test_detector_must_be_integer(detector):
    with pytest.raises(ValueError):
        region({"ra": 1, "dec": 2, "detector": detector})


@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", ["/api/v1/reports", "/api/v1/candidates"])
def test_bad_uuid_is_client_error(client, endpoint):
    r = client.post(endpoint, json.dumps({"sequence": "not-a-uuid"}), content_type="application/json")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_request"


@pytest.mark.django_db
def test_outside_grid_mark_rejected(client):
    s = region({"ra": 269.452075, "dec": 4.693391})
    w, shape = grid(s)
    seq = Sequence.objects.create(
        cache_key="field-validation",
        manifest={
            "frames": [{}],
            "geometry": {"mode": "celestial", "wcs": w.to_header().tostring(), "width": shape[1], "height": shape[0]},
        },
    )
    r = client.post(
        "/api/v1/candidates",
        json.dumps({"sequence": str(seq.id), "frame": 0, "ra": 0, "dec": 0}),
        content_type="application/json",
    )
    assert r.status_code == 400
    assert "outside" in r.json()["error"]["message"]


def test_archive_503_is_actionable_and_does_not_expose_url():
    response = requests.Response()
    response.status_code = 503
    error = archive_error(requests.HTTPError("503 for url: https://example.invalid/long-path", response=response))
    assert error["retryable"]
    assert "503" in error["message"]
    assert "https://" not in error["message"]


@pytest.mark.django_db
def test_retry_preserves_previous_manifest(client):
    s = region({"ra": 1, "dec": 2})
    old = Sequence.objects.create(
        cache_key="partial-retry", manifest={"selection": s, "frames": [], "excluded": [{"id": "obs", "reason": "503"}]}
    )
    r = client.post(
        "/api/v1/searches", json.dumps({**s, "retry_sequence": str(old.id)}), content_type="application/json"
    )
    assert r.status_code == 202
    assert r.json()["selection"]["retry_of"] == str(old.id)
    old.refresh_from_db()
    assert len(old.manifest["excluded"]) == 1
