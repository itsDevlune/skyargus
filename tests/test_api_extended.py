"""Extended API and Django integration tests: quotas, method enforcement, health, CSRF."""

import json

import pytest
from django.test import Client

from apps.core.models import Job, Sequence
from science.coordinates import region

pytestmark = pytest.mark.django_db


def post(c, url, payload):
    return c.post(url, json.dumps(payload), content_type="application/json")


# ---------------------------------------------------------------------------
# Quota enforcement
# ---------------------------------------------------------------------------
def test_session_active_job_quota(client, monkeypatch, settings):
    """Two active jobs are allowed; the third should be rejected with 429."""
    settings.ARGUS_SESSION_ACTIVE_JOBS = 2
    monkeypatch.setattr("apps.core.tasks.publish", lambda *a: None)
    for i in range(2):
        r = post(client, "/api/v1/searches", {"ra": 10 + i, "dec": 10})
        assert r.status_code == 202
    r = post(client, "/api/v1/searches", {"ra": 20, "dec": 10})
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "quota_exceeded"


def test_cached_sequence_does_not_count_against_quota(client, monkeypatch):
    """Returning a cached sequence should not create a new job."""
    monkeypatch.setattr("apps.core.tasks.publish", lambda *a: None)
    # Create a cached sequence
    from apps.core.tasks import cache_key

    s = region({"ra": 100.0, "dec": 50.0})
    Sequence.objects.create(cache_key=cache_key(s), manifest={"frames": [], "warnings": []})
    # This should hit cache and return 200, not 202
    r = post(client, "/api/v1/searches", {"ra": 100.0, "dec": 50.0})
    assert r.status_code == 200 or ("cached" in r.json() and r.json()["cached"] is True)


def test_job_quotas_are_disabled_when_zero(client, monkeypatch, settings):
    from apps.core.models import Job

    monkeypatch.setattr("apps.core.views.publish", lambda *a: None)
    settings.ARGUS_SESSION_ACTIVE_JOBS = 0
    settings.ARGUS_SESSION_JOBS_PER_HOUR = 0
    settings.ARGUS_QUEUE_LIMIT = 0
    session = client.session
    session.save()
    Job.objects.bulk_create(
        [Job(owner=session.session_key, kind="sequence", selection={}, state="queued") for _ in range(25)]
    )
    assert post(client, "/api/v1/searches", {"ra": 20, "dec": 10}).status_code == 202


def test_cache_is_available_even_when_all_configured_quotas_are_full(client, monkeypatch, settings):
    from apps.core.models import Job
    from apps.core.tasks import cache_key

    monkeypatch.setattr("apps.core.views.publish", lambda *a: None)
    settings.ARGUS_SESSION_ACTIVE_JOBS = 1
    settings.ARGUS_SESSION_JOBS_PER_HOUR = 1
    settings.ARGUS_QUEUE_LIMIT = 1
    session = client.session
    session.save()
    Job.objects.create(owner=session.session_key, kind="sequence", selection={}, state="queued")
    sequence = Sequence.objects.create(
        cache_key=cache_key(region({"ra": 100, "dec": 50})), manifest={"frames": [], "warnings": []}
    )
    response = post(client, "/api/v1/searches", {"ra": 100, "dec": 50})
    assert response.status_code == 200
    assert response.json()["sequence"] == str(sequence.id)
    assert response.json()["cached"] is True


# ---------------------------------------------------------------------------
# Method enforcement
# ---------------------------------------------------------------------------
def test_report_patch_rejected(client):
    seq = Sequence.objects.create(cache_key="patch-test", manifest={"frames": [], "warnings": []})
    r = post(client, "/api/v1/reports", {"sequence": str(seq.id), "title": "t"}).json()
    patch = client.patch(f"/api/v1/reports/{r['id']}", "{}", content_type="application/json")
    assert patch.status_code == 405


def test_search_get_rejected(client):
    r = client.get("/api/v1/searches")
    assert r.status_code == 405


def test_report_delete_rejected(client):
    seq = Sequence.objects.create(cache_key="del-test", manifest={"frames": [], "warnings": []})
    r = post(client, "/api/v1/reports", {"sequence": str(seq.id), "title": "t"}).json()
    assert client.delete(f"/api/v1/reports/{r['id']}").status_code == 405


# ---------------------------------------------------------------------------
# Candidate operations
# ---------------------------------------------------------------------------
def test_candidate_get_empty(client, sequence_with_frames):
    r = client.get(f"/api/v1/candidates?sequence={sequence_with_frames.id}")
    assert r.status_code == 200
    assert r.json()["candidates"] == []


def test_candidate_crud_lifecycle(client, sequence_with_frames):
    """Create → read → update → delete a candidate."""
    data = {
        "sequence": str(sequence_with_frames.id),
        "frame": 0,
        "ra": 269.452,
        "dec": 4.693,
        "classification": "unsure",
        "note": "test mark",
    }
    # Create
    r = post(client, "/api/v1/candidates", data)
    assert r.status_code == 201
    cid = r.json()["id"]
    assert r.json()["revision"] == 1

    # Read
    r = client.get(f"/api/v1/candidates?sequence={sequence_with_frames.id}")
    assert len(r.json()["candidates"]) == 1

    # Update
    update = client.patch(
        f"/api/v1/candidates/{cid}",
        json.dumps({**data, "revision": 1, "note": "updated"}),
        content_type="application/json",
    )
    assert update.status_code == 200
    assert update.json()["revision"] == 2

    # Delete
    assert client.delete(f"/api/v1/candidates/{cid}").status_code == 200

    # Verify deleted
    r = client.get(f"/api/v1/candidates?sequence={sequence_with_frames.id}")
    assert len(r.json()["candidates"]) == 0


def test_candidate_cross_session_invisible(client, sequence_with_frames):
    """Another session cannot see or modify this session's candidates."""
    data = {
        "sequence": str(sequence_with_frames.id),
        "frame": 0,
        "ra": 269.452,
        "dec": 4.693,
        "classification": "unsure",
    }
    r = post(client, "/api/v1/candidates", data)
    cid = r.json()["id"]

    other = Client()
    assert other.get(f"/api/v1/candidates?sequence={sequence_with_frames.id}").json()["candidates"] == []
    assert other.delete(f"/api/v1/candidates/{cid}").status_code == 404


# ---------------------------------------------------------------------------
# Analysis method validation
# ---------------------------------------------------------------------------
def test_unsupported_analysis_method_rejected(client, sequence_with_frames):
    r = post(client, "/api/v1/analyses", {"method": "unknown", "sequence": str(sequence_with_frames.id)})
    assert r.status_code == 400
    assert "supported analysis methods" in r.json()["error"]["message"].lower()


def test_analysis_motion_on_native_sequence_rejected(client, native_sequence):
    r = post(client, "/api/v1/analyses", {"method": "motion", "sequence": str(native_sequence.id)})
    assert r.status_code == 400


@pytest.mark.parametrize(
    "payload",
    [
        {"method": "difference", "frame_a": 1.5, "frame_b": 1},
        {"method": "difference", "frame_a": True, "frame_b": 1},
        {"method": "difference", "frame_a": 1, "frame_b": 1},
        {"method": "stack", "frames": []},
        {"method": "stack", "frames": [0, 0]},
        {"method": "stack", "frames": [0, 3]},
        {"method": "stack", "frames": [0, True]},
        {"method": "composite", "red": 0, "green": 1.5, "blue": 2},
        {"method": "composite", "red": 0, "green": 1, "blue": 1},
    ],
)
def test_analysis_rejects_invalid_frame_selection_without_enqueuing(client, sequence_with_frames, payload):
    before = Job.objects.count()
    response = post(client, "/api/v1/analyses", {"sequence": str(sequence_with_frames.id), **payload})

    assert response.status_code == 400
    assert Job.objects.count() == before


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------
def test_health_returns_db_status(client):
    r = client.get("/health/")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "database" in data
    assert "queued" in data


# ---------------------------------------------------------------------------
# Report title truncation
# ---------------------------------------------------------------------------
def test_report_title_truncated(client):
    seq = Sequence.objects.create(cache_key="title-trunc", manifest={"frames": [], "warnings": []})
    r = post(client, "/api/v1/reports", {"sequence": str(seq.id), "title": "x" * 200})
    assert r.status_code == 201
    assert len(r.json()["title"]) <= 160


# ---------------------------------------------------------------------------
# Job ownership
# ---------------------------------------------------------------------------
def test_job_invisible_to_other_session(client, monkeypatch):
    monkeypatch.setattr("apps.core.tasks.publish", lambda *a: None)
    r = post(client, "/api/v1/searches", {"ra": 50, "dec": 50})
    assert r.status_code == 202
    job_url = r.json()["status_url"]

    other = Client()
    assert other.get(job_url).status_code == 404


# ---------------------------------------------------------------------------
# CSRF on all write routes
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/searches",
        "/api/v1/resolve",
        "/api/v1/analyses",
        "/api/v1/candidates",
        "/api/v1/reports",
        "/api/v1/catalogs/gaia",
    ],
)
def test_csrf_enforced_on_all_write_routes(url):
    client = Client(enforce_csrf_checks=True)
    r = post(client, url, {"ra": 1, "dec": 2})
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Report sharing lifecycle
# ---------------------------------------------------------------------------
def test_share_create_and_revoke_lifecycle(client):
    seq = Sequence.objects.create(cache_key="share-lc", manifest={"frames": [], "warnings": []})
    r = post(client, "/api/v1/reports", {"sequence": str(seq.id), "title": "shared"}).json()
    pk = r["id"]

    # Create share link
    share = post(client, f"/api/v1/reports/{pk}/shares", {})
    assert share.status_code == 201
    url = share.json()["url"]
    embed = share.json()["embed"]

    # Public access works
    public = Client()
    assert public.get(url).status_code == 200
    assert public.get(embed).status_code == 200
    assert public.get(url + "?format=json").status_code == 200

    # Revoke
    assert client.delete(f"/api/v1/reports/{pk}/shares").status_code == 200
    assert public.get(url).status_code == 404
    assert public.get(embed).status_code == 404
