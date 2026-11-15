import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from apps.core.network import get

versions = json.loads(Path("docs/evidence/tutorial-provenance.json").read_text())
records = []
for repo, paths in [
    ("Caltech-IPAC/irsa-tutorials", ["tutorials/spherex/spherex_cutouts.md", "tutorials/spherex/spherex_psf.md"]),
    (
        "asc-csa/NEOSSAT_Tutorial",
        ["code/01_ Extracting Data and Visualization.ipynb", "code/02_Pre Processing and Analysis.ipynb"],
    ),
]:
    for path in paths:
        commit = versions[repo]["commit"]
        url = f"https://raw.githubusercontent.com/{repo}/{commit}/" + quote(path, safe="/")
        raw = get(url, limit=16 * 1024 * 1024)
        records.append(
            {
                "repository": repo,
                "commit": commit,
                "path": path,
                "url": url,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
            }
        )
notes = {
    "sources": records,
    "spherex": "Cutout tutorial uses TAP with observation timestamps, spatial WCS then alternate W spectral lookup with SIP removed, retains primary processing version, excludes failed cutouts. Argus instead uses bounded documented SIA2/IBE and bilinear lookup tested against WCS-TAB. PSF tutorial distinguishes detector-zone ePSF extraction and raw-coordinate offsets. Quantitative PSF workflow not yet implemented.",
    "neossat": "Tutorial 01 provides NEOSSAT-only CADC spatial discovery. Tutorial 02 covers calibrated plane filtering, overscan medians, master dark subtraction and streaklet detection. Its illustrative last-50-column overscan assumption is unsuitable for our sample, whose header BIASSEC is first 64 columns and DATASEC is columns 473–728. Argus therefore reads actual DATASEC and labels raw counts; no guessed dark/overscan correction or sky motion.",
    "adaptation": "Independent provider implementation informed by these methods, not copied notebook source. Repository license text and commits retained in tutorial-provenance.json. Broader calibrated analysis remains incomplete.",
}
Path("docs/evidence/tutorial-methods.json").write_text(json.dumps(notes, indent=2), encoding="utf8")
print("Pinned and inspected", len(records), "tutorial sources")
