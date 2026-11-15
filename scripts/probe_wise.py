import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from apps.core.network import get

raw = get(
    "https://irsa.ipac.caltech.edu/ibe/search/wise/allwise/p3am_cdd",
    {"POS": "269.452075,4.693391"},
    limit=1024 * 1024,
)
Path("docs/evidence/wise-metadata.tbl").write_bytes(raw)
print(raw.decode()[:2500])
