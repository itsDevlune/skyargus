import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from apps.core.network import get

query = "SELECT TOP 10 O.observationID,P.productID,P.planeURI,A.uri FROM caom2.Observation AS O JOIN caom2.Plane AS P ON O.obsID=P.obsID JOIN caom2.Artifact AS A ON P.planeID=A.planeID WHERE O.collection='NEOSSAT' AND O.observationID='2019312133024'"
print(
    get(
        "https://ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/argus/sync", {"LANG": "ADQL", "FORMAT": "csv", "QUERY": query}
    ).decode()
)
