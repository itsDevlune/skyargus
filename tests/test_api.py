import json

import pytest
from django.test import Client

from apps.core.models import Job, Sequence
from apps.core.network import get

pytestmark = pytest.mark.django_db


def post(c, url, payload):
    return c.post(url, json.dumps(payload), content_type="application/json")


@pytest.fixture
def sequence():
    return Sequence.objects.create(
        cache_key="a" * 64,
        manifest={"id": "test", "frames": [{"id": "obs1"}], "warnings": ["not assessed"], "selection": {}},
    )


def test_home_and_validation(client):
    assert client.get("/").status_code == 200
    assert post(client, "/api/v1/searches", {"ra": 360, "dec": 0}).status_code == 400
    assert post(client, "/api/v1/searches", {"ra": 1, "dec": 0, "source": "unknown"}).status_code == 400


def test_job_persistence_and_ownership(client):
    response = post(client, "/api/v1/searches", {"ra": 1, "dec": 0})
    assert response.status_code == 202
    job = Job.objects.get(pk=response.json()["job"])
    assert job.dispatch is not None
    url = response.json()["status_url"]
    assert Client().get(url).status_code == 404
    assert post(client, url, {"action": "cancel"}).json()["state"] == "cancelled"


def test_immutable_report_sharing_revocation(client, sequence):
    payload = {"sequence": str(sequence.id), "title": "<script>unsafe</script>"}
    r = post(client, "/api/v1/reports", payload)
    assert r.status_code == 201
    pk = r.json()["id"]
    assert Client().get("/api/v1/reports/" + pk).status_code == 404
    assert client.patch("/api/v1/reports/" + pk, "{}", content_type="application/json").status_code == 405
    link = post(client, "/api/v1/reports/" + pk + "/shares", {}).json()["url"]
    public = Client()
    assert public.get(link + "?format=json").json()["title"] == "<script>unsafe</script>"
    assert b"<script>unsafe</script>" not in public.get(link).content
    assert client.delete("/api/v1/reports/" + pk + "/shares").status_code == 200
    assert public.get(link).status_code == 404


def test_embed_has_no_scripts_or_write_controls(client, sequence):
    r = post(client, "/api/v1/reports", {"sequence": str(sequence.id), "title": "read only"}).json()
    link = post(client, "/api/v1/reports/" + r["id"] + "/shares", {}).json()["embed"]
    response = Client().get(link)
    assert response.status_code == 200
    assert b"<script" not in response.content
    assert b"<button" not in response.content
    assert "script-src 'none'" in response["Content-Security-Policy"]
    assert "frame-ancestors 'self'" in response["Content-Security-Policy"]
    assert Client().post(link).status_code == 405


def test_candidate_conflict_and_private(client, sequence):
    data = {"sequence": str(sequence.id), "frame": 0, "ra": 1, "dec": 2, "classification": "unsure", "note": "check"}
    c = post(client, "/api/v1/candidates", data).json()
    url = "/api/v1/candidates/" + c["id"]
    assert Client().delete(url).status_code == 404
    response = client.patch(url, json.dumps({**data, "revision": 0}), content_type="application/json")
    assert response.status_code == 409
    assert (
        client.patch(url, json.dumps({**data, "revision": 1}), content_type="application/json").json()["revision"] == 2
    )


def test_csrf_enforced():
    client = Client(enforce_csrf_checks=True)
    assert post(client, "/api/v1/searches", {"ra": 1, "dec": 2}).status_code == 403


@pytest.mark.parametrize(
    "url",
    [
        "http://irsa.ipac.caltech.edu/file",
        "https://localhost/file",
        "https://127.0.0.1/file",
        "https://irsa.ipac.caltech.edu:444/file",
        "https://user@irsa.ipac.caltech.edu/file",
    ],
)
def test_ssrf_rejected_before_network(url):
    with pytest.raises(ValueError):
        get(url)
