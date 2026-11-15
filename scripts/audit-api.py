"""Additional local API edge-case audit. No external requests; creates one private audit mark."""

import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

base = "http://127.0.0.1:8000"
s = requests.Session()
s.get(base + "/", timeout=10)
s.headers["X-CSRFToken"] = s.cookies.get("csrftoken", "")
records = []


def check(name, url, data, expected, method="POST"):
    r = s.request(method, base + url, json=data, timeout=10)
    records.append(
        {
            "name": name,
            "status": "PASS" if r.status_code in expected else "FAIL",
            "http_status": r.status_code,
            "expected": expected,
        }
    )
    if r.status_code == 202 and 202 not in expected:
        # Cancel unexpectedly accepted audit input before the worker can download it.
        s.post(base + r.json()["status_url"], json={"action": "cancel"}, timeout=10)
    return r


for payload, label in [
    ({"ra": float("nan"), "dec": 0}, "nonfinite"),
    ({"ra": 1, "dec": 91}, "declination range"),
    ({"ra": 1, "dec": 2, "width": 0}, "FOV lower bound"),
    ({"ra": 1, "dec": 2, "height": 21}, "FOV upper bound"),
    ({"ra": "24:00:00", "dec": "0:00:00", "unit": "hourangle"}, "24 hours out of range"),
    ({"ra": 1, "dec": 2, "start": "2026-01-03", "end": "2026-01-01"}, "reversed dates"),
]:
    # Requests rejects JSON NaN itself; raw body tests server nonfinite handling.
    if label == "nonfinite":
        r = s.post(
            base + "/api/v1/searches",
            data='{"ra":NaN,"dec":0}',
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        records.append(
            {
                "name": label,
                "status": "PASS" if r.status_code == 400 else "FAIL",
                "http_status": r.status_code,
                "expected": [400],
            }
        )
    else:
        check(label, "/api/v1/searches", payload, [400])
check("Malformed report sequence UUID gives client error", "/api/v1/reports", {"sequence": "not-a-uuid"}, [400, 404])
check(
    "Malformed candidate sequence UUID gives client error",
    "/api/v1/candidates",
    {"sequence": "not-a-uuid", "frame": 0, "ra": 1, "dec": 2},
    [400, 404],
)
check("Unsupported analysis is explicit", "/api/v1/analyses", {"method": "spectrum"}, [400])
check(
    "Unknown job identifier does not expose another job",
    "/api/v1/jobs/00000000-0000-0000-0000-000000000000",
    None,
    [404],
    method="GET",
)
manifests = json.loads(Path("docs/evidence/real-manifests.json").read_text(encoding="utf8"))
seq = next(x for x in manifests if x["selection"]["source"] == "spherex" and len(x["frames"]) == 8)
r = check(
    "Off-field annotation is rejected",
    "/api/v1/candidates",
    {
        "sequence": seq["id"],
        "frame": 0,
        "ra": 0,
        "dec": 0,
        "note": "API audit: deliberately off-field coordinate",
        "classification": "unsure",
    },
    [400, 422],
)
if r.status_code == 201:
    # Remove only the mark this audit created, through its own authorized private session.
    s.delete(base + "/api/v1/candidates/" + r.json()["id"], json={}, timeout=10)
from science.coordinates import region

try:
    selection = region({"ra": 1, "dec": 2, "detector": 3.9})
    records.append(
        {
            "name": "Fractional detector enum rejected",
            "status": "FAIL",
            "detail": f"3.9 silently normalized to {selection['detector']}",
        }
    )
except ValueError:
    records.append({"name": "Fractional detector enum rejected", "status": "PASS"})
Path("docs/evidence/application-audit/api-results.json").write_text(json.dumps(records, indent=2), encoding="utf8")
print(json.dumps(records, indent=2))
