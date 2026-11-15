"""Opt-in bounded real provider checks. Writes reproducible evidence without network in routine tests."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "argus.settings")
import django

django.setup()
from apps.core.models import Dispatch, Job
from apps.core.providers import discovery, gaia, neossat, resolve
from apps.core.tasks import run_job
from science.coordinates import region

targets = ["Barnard's Star", "Epsilon Indi B", "WISE J085510.83-071442.5", "RW Aur", "R Dra"]
evidence = {"targets": [], "checks": {}}
for name in targets:
    item = {"name": name}
    try:
        position = resolve(name)
        item["resolution"] = position
        s = region({**position, "detector": 3})
        rows, meta = discovery(s)
        item["discovery"] = meta
        item["observations"] = rows
    except Exception as exc:
        item["error"] = str(exc)
    evidence["targets"].append(item)
    print(name, len(item.get("observations", [])), item.get("error", "OK"), flush=True)
for name, func in [("gaia_dr3", gaia), ("neossat", neossat)]:
    try:
        evidence["checks"][name] = func(region({"ra": 269.452075, "dec": 4.693391, "detector": 3}))
    except Exception as exc:
        evidence["checks"][name] = {"error": str(exc)}
    print(name, str(evidence["checks"][name])[:300], flush=True)
path = Path("docs/evidence")
path.mkdir(parents=True, exist_ok=True)
(path / "provider-probes.json").write_text(json.dumps(evidence, indent=2), encoding="utf8")
if "--cutouts" in sys.argv:
    s = region({"ra": 269.452075, "dec": 4.693391, "detector": 3, "width": 6, "height": 6})
    job = Job.objects.create(owner="bounded-verification", selection=s)
    Dispatch.objects.create(job=job)
    run_job(str(job.id))
    job.refresh_from_db()
    (path / "real-job.json").write_text(
        json.dumps({"job": str(job.id), "state": job.state, "result": job.result, "error": job.error}, indent=2)
    )
    print("real job", job.state, job.result, job.error, flush=True)
