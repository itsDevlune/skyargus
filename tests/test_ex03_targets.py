import json
import math
from pathlib import Path


def test_all_five_challenge_targets_have_bounded_resolution_provenance():
    evidence_path = Path(__file__).parents[1] / "docs/evidence/provider-probes.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    targets = {target["name"]: target for target in evidence["targets"]}
    expected = {
        "Barnard's Star",
        "Epsilon Indi B",
        "WISE J085510.83-071442.5",
        "RW Aur",
        "R Dra",
    }

    assert set(targets) == expected
    for name, target in targets.items():
        resolution = target["resolution"]
        assert resolution["name"]
        assert "CDS Sesame / IDIA mirror" in resolution["resolver"]
        assert "J2000" in resolution["epoch"]
        assert "Proper motion not applied" in resolution["epoch"]
        assert math.isfinite(resolution["ra"])
        assert 0 <= resolution["ra"] < 360
        assert math.isfinite(resolution["dec"])
        assert -90 <= resolution["dec"] <= 90
        assert target["discovery"]["metadata_limit"] == 100
        assert target["observations"]
        assert all(frame["source"] == "SPHEREx" for frame in target["observations"])
        assert name

