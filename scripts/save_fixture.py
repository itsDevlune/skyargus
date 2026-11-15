import hashlib
import json
import shutil
from pathlib import Path

from astropy.io import fits

root = Path("tests/fixtures/real")
root.mkdir(parents=True, exist_ok=True)
for path in Path("data/downloads").glob("*.fits"):
    with fits.open(path) as h:
        if "IMAGE" in h and h["IMAGE"].header.get("OBSID") == "2025W33_2C_0321_1":
            shutil.copyfile(path, root / "spherex-dr1-cutout.fits")
            meta = {
                "id": h["IMAGE"].header["OBSID"],
                "release": "DR1",
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "real_observation": True,
                "source": "https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W33_2C/l2b-v27-2026-228/3/level2_2025W33_2C_0321_1D3_spx_l2b-v27-2026-228.fits",
                "cutout": {"center": "269.452075,4.693391deg", "size": "9.758073580374354arcmin", "gzip": "false"},
                "acknowledgement": "See templates/sources.html and docs/SOURCES.md. Public SPHEREx observation, not a synthetic fixture.",
            }
            (root / "provenance.json").write_text(json.dumps(meta, indent=2))
            break
