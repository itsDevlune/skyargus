import json

import pytest
from django.test import Client

from apps.core.models import Report, Sequence

pytestmark = pytest.mark.django_db


def post(c, data):
    return c.post("/api/v1/reports", json.dumps(data), content_type="application/json")


def test_revision_chain_is_immutable_and_conflicts(client):
    seq = Sequence.objects.create(cache_key="revisions", manifest={"frames": [], "warnings": []})
    payload = {"sequence": str(seq.id), "title": "first"}
    first = post(client, payload).json()
    second = post(client, {**payload, "title": "second", "parent": first["id"]}).json()
    assert second["revision"] == 2
    assert second["parent"] == first["id"]
    assert second["investigation"] == first["id"]
    assert Report.objects.get(pk=first["id"]).snapshot["title"] == "first"
    assert post(client, {**payload, "parent": first["id"]}).status_code == 409
    assert post(Client(), {**payload, "parent": second["id"]}).status_code == 404
