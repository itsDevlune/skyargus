from unittest.mock import patch

import pytest
from django.http import JsonResponse

from apps.core.providers import wise
from science.coordinates import region


def test_wise_catalog_query_and_provenance():
    selection = region({"ra": 269.452075, "dec": 4.693391})
    csv = b'designation,ra,dec,w1mpro,w2mpro,ph_qual,cc_flags\nJ175748,269.452075,4.693391,9.1,8.9,AAUU,0000\n'
    with patch("apps.core.providers.get", return_value=csv) as fetch:
        result = wise(selection)
    assert result["sources"][0]["designation"] == "J175748"
    assert float(result["sources"][0]["ra"]) == selection["ra"]
    assert result["propagated"] is False
    assert result["possibly_truncated"] is False
    assert "allwise_p3as_psd" in fetch.call_args.args[1]["QUERY"]
    assert "TOP 200" in fetch.call_args.args[1]["QUERY"]
    assert fetch.call_args.kwargs["limit"] == 1024 * 1024


@pytest.mark.django_db
def test_wise_endpoint_queues_bounded_request(client):
    with patch("apps.core.views.enqueue", return_value=JsonResponse({"queued": True})) as enqueue:
        response = client.post("/api/v1/catalogs/wise", {"ra": 10, "dec": 20}, content_type="application/json")
    assert response.status_code == 200
    assert enqueue.call_args.args[2] == "wise"


@pytest.mark.django_db
def test_wise_endpoint_rejects_invalid_coordinates(client):
    response = client.post("/api/v1/catalogs/wise", {"ra": 10, "dec": 91}, content_type="application/json")
    assert response.status_code == 400
