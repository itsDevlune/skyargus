"""Bounded public CADC artifact discovery and native raw-detector display."""

import io
import re
from urllib.parse import quote

import numpy as np
from astropy.io import fits
from astropy.table import Table

from science.coordinates import footprint_search_radius_deg

from .network import get

ENDPOINT = "https://ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/argus/sync"


def discover(s):
    radius = footprint_search_radius_deg(s["width"], s["height"])
    where = f"O.collection='NEOSSAT' AND INTERSECTS(CIRCLE('ICRS',{s['ra']},{s['dec']},{radius}),P.position_bounds)=1"
    from astropy.time import Time

    if s.get("start"):
        where += f" AND P.time_bounds_lower>={Time(s['start']).mjd}"
    if s.get("end"):
        where += f" AND P.time_bounds_lower<{Time(s['end']).mjd + 1}"
    query = f"SELECT TOP 40 O.observationID,P.productID,P.planeURI,P.time_bounds_lower,P.time_bounds_upper,A.uri FROM caom2.Observation AS O JOIN caom2.Plane AS P ON O.obsID=P.obsID JOIN caom2.Artifact AS A ON P.planeID=A.planeID WHERE {where} AND P.productID='raw' AND A.uri LIKE '%.fits' ORDER BY P.time_bounds_lower,O.observationID"
    raw = get(ENDPOINT, {"LANG": "ADQL", "QUERY": query, "FORMAT": "csv"}, limit=2 * 1024 * 1024)
    t = Table.read(io.BytesIO(raw), format="ascii.csv")
    rows = []
    for r in t[:4]:
        uri = str(r["uri"])
        if not uri.startswith("cadc:NEOSSAT/"):
            continue
        filename = uri.split("/", 1)[1]
        if "/" in filename or ".." in filename:
            continue
        rows.append(
            {
                "id": str(r["observationID"]),
                "url": "https://ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/data/pub/NEOSSAT/" + quote(filename),
                "artifact_uri": uri,
                "plane_uri": str(r["planeURI"]),
                "mjd": float(r["time_bounds_lower"]),
                "end_mjd": float(r["time_bounds_upper"]),
                "release": "CADC raw",
                "source": "NEOSSat",
                "detector": "optical CCD",
            }
        )
    return rows, {
        "endpoint": ENDPOINT,
        "returned_metadata": len(t),
        "metadata_limit": 40,
        "download_limit": 4,
        "selection": "Earliest 4 raw FITS products in bounded sky/date search",
        "warning": "Native detector mode: uncalibrated raw counts, pointing/tracking vary. Detector displacements are not sky motion.",
    }


def read_native(raw):
    with fits.open(io.BytesIO(raw), memmap=False) as h:
        header = h[0].header
        if header.get("NAXIS1", 0) * header.get("NAXIS2", 0) > 2048**2:
            raise ValueError("NEOSSat pixel budget exceeded")
        array = np.asarray(h[0].data, dtype=float)
        # Display only documented DATASEC; preserve the full native FITS separately.
        section = str(header.get("DATASEC", ""))
        match = re.fullmatch(r"\[(\d+):(\d+),(\d+):(\d+)\]", section)
        if not match:
            raise ValueError("NEOSSat DATASEC required for native science-region display")
        x1, x2, y1, y2 = map(int, match.groups())
        array = array[y1 - 1 : y2, x1 - 1 : x2]
        return (
            array,
            None,
            {
                "units": "raw ADU (uncalibrated)",
                "date": header.get("DATE-OBS"),
                "timescale": header.get("TIMESYS"),
                "wavelength": None,
                "wavelength_reason": "Broad optical CLEAR passband; not a SPHEREx spectral channel",
                "coverage_fraction": float(np.isfinite(array).mean()),
                "header": None,
                "native_shape": list(array.shape),
                "flag_values": [],
                "alignment": "Native detector coordinates; no celestial registration",
                "mask_policy": "DATASEC crop only. No overscan/dark correction applied. Raw archive file retained.",
                "variance": "No calibrated uncertainty available. Raw counts are not calibrated source flux.",
                "data_section": section,
                "tracking": str(header.get("MODE", header.get("TRK_MODE", "Not assessed"))),
                "geometry_mode": "native",
            },
        )
