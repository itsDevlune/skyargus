import json
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from apps.core.network import get

provenance = json.loads(Path("docs/evidence/tutorial-provenance.json").read_text())
repo = "asc-csa/NEOSSAT_Tutorial"
record = provenance[repo]
for name in ["code/01_ Extracting Data and Visualization.ipynb", "code/02_Pre Processing and Analysis.ipynb"]:
    url = f"https://raw.githubusercontent.com/{repo}/{record['commit']}/" + quote(name, safe="/")
    data = json.loads(get(url, limit=16 * 1024 * 1024))
    print("\nNOTEBOOK", name)
    cells = ["".join(c.get("source", [])) for c in data["cells"]]
    for cell in cells:
        if any(
            term in cell.lower()
            for term in ["overscan", "dark", "bias", "cadc", "query", "fits.getdata", "sigma", "license", "align"]
        ):
            print(cell[:2200])
repo = "Caltech-IPAC/irsa-tutorials"
commit = provenance[repo]["commit"]
tree = json.loads(get(f"https://api.github.com/repos/{repo}/git/trees/{commit}?recursive=1", limit=4 * 1024 * 1024))
print("SPHEREX FILES", [x["path"] for x in tree["tree"] if "spherex" in x["path"].lower()][:30])
