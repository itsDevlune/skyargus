import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from apps.core.network import get

out = {}
for repo in ["Caltech-IPAC/irsa-tutorials", "asc-csa/NEOSSAT_Tutorial"]:
    record = {}
    for name, url in [
        ("commit", f"https://api.github.com/repos/{repo}/commits/main"),
        ("license", f"https://api.github.com/repos/{repo}/license"),
        ("tree", f"https://api.github.com/repos/{repo}/git/trees/main?recursive=1"),
    ]:
        try:
            result = json.loads(get(url, limit=2 * 1024 * 1024))
            if name == "commit":
                record["commit"] = result["sha"]
            elif name == "tree":
                record["notebooks"] = [x["path"] for x in result["tree"] if x["path"].endswith(".ipynb")]
            else:
                import base64

                record["license"] = base64.b64decode(result.get("content", "")).decode()
                record["license_name"] = result.get("license", {}).get("name")
        except Exception as exc:
            record[name + "_error"] = str(exc)
    out[repo] = record
Path("docs/evidence/tutorial-provenance.json").write_text(json.dumps(out, indent=2), encoding="utf8")
print({k: {x: y for x, y in v.items() if x != "license"} for k, v in out.items()})
