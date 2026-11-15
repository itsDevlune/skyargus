import io

from astropy.table import Table
from astropy.time import Time

from apps.core.providers import discovery
from science.coordinates import region


def test_inclusive_end_day_passed_to_sia(monkeypatch):
    received = {}
    empty = Table(names=["access_url", "obs_id", "t_min"], dtype=["U1", "U1", float])
    out = io.BytesIO()
    empty.write(out, format="votable")

    def fetch(url, params, **kwargs):
        received.update(params)
        return out.getvalue()

    monkeypatch.setattr("apps.core.providers.get", fetch)
    s = region({"ra": 1, "dec": 2, "start": "2025-05-07", "end": "2025-05-07"})
    discovery(s)
    start, end = map(float, received["TIME"].split())
    assert start == Time("2025-05-07").mjd
    assert end - start == 1
    assert s["date_policy"] == "inclusive-utc-days-v1"
