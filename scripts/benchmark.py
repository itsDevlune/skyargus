import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "argus.settings")
import django

django.setup()
import numpy as np

from apps.core.models import Job, Sequence
from apps.core.tasks import run_job
from science.coordinates import region
from science.imaging import preview, read_frame

sequence = Sequence.objects.filter(manifest__selection__source="spherex").last()
raw = Path("tests/fixtures/real/spherex-dr1-cutout.fits").read_bytes()
started = time.perf_counter()
cpu = time.process_time()
for _ in range(8):
    array, flags, meta = read_frame(raw, region({"ra": 269.452075, "dec": 4.693391, "detector": 3}))
    low, high = np.nanpercentile(array, [1, 99.5])
    preview(array, low, high)
result = {
    "scope": "Eight repeated processing passes over one real observational fixture. Not eight independent observations or a cold network benchmark.",
    "processing_seconds": time.perf_counter() - started,
    "cpu_seconds": time.process_time() - cpu,
    "fixture_bytes": len(raw),
}
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (n, ctypes.c_size_t)
            for n in [
                "PeakWorkingSetSize",
                "WorkingSetSize",
                "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage",
                "QuotaPeakNonPagedPoolUsage",
                "QuotaNonPagedPoolUsage",
                "PagefileUsage",
                "PeakPagefileUsage",
            ]
        ]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    ctypes.windll.kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    ok = ctypes.windll.psapi.GetProcessMemoryInfo(
        ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
    )
    result["peak_process_working_set_bytes"] = counters.PeakWorkingSetSize if ok else None
if sequence:
    job = Job.objects.create(owner="cache-benchmark", selection=sequence.manifest["selection"])
    started = time.perf_counter()
    run_job(str(job.id))
    result["cached_job_seconds"] = time.perf_counter() - started
result["real_sequence_metrics"] = [
    {
        "id": str(s.id),
        "source": s.manifest["selection"]["source"],
        "frames": len(s.manifest["frames"]),
        "metrics": s.manifest.get("metrics"),
    }
    for s in Sequence.objects.all()
]
Path("docs/evidence/performance.json").write_text(json.dumps(result, indent=2))
print(result)
