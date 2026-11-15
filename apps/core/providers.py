import io
import math
from pathlib import Path

from astropy.table import Table
from astropy.time import Time

from science.coordinates import footprint_search_radius_deg

from .network import get

SIA = "https://irsa.ipac.caltech.edu/SIA"


def select_epochs(rows, limit):
    """Maximize temporal spread within the bounded metadata sample, including endpoints."""
    dated = sorted([r for r in rows if r.get("mjd") is not None], key=lambda r: (r["mjd"], r["id"]))
    if len(dated) <= limit:
        return dated + [r for r in rows if r.get("mjd") is None][: max(0, limit - len(dated))]
    chosen = {0, len(dated) - 1}
    while len(chosen) < limit:
        remaining = [i for i in range(len(dated)) if i not in chosen]
        index = max(remaining, key=lambda i: (min(abs(dated[i]["mjd"] - dated[j]["mjd"]) for j in chosen), -i))
        chosen.add(index)
    return [dated[i] for i in sorted(chosen)]


def discovery(s):
    if s["source"] == "neossat":
        from .neossat import discover

        return discover(s)
    radius = footprint_search_radius_deg(s["width"], s["height"])
    params = {"COLLECTION": "spherex_" + s["release"], "POS": f"CIRCLE {s['ra']} {s['dec']} {radius}", "MAXREC": 100}
    if s["start"] or s["end"]:
        params["TIME"] = (
            f"{Time(s['start']).mjd if s['start'] else '-Inf'} {Time(s['end']).mjd + 1 if s['end'] else '+Inf'}"
        )
    ranges = [(0.75, 1.09), (1.10, 1.62), (1.63, 2.41), (2.42, 3.82), (3.83, 4.41), (4.42, 5.00)]
    a, b = ranges[s["detector"] - 1]
    params["BAND"] = f"{a * 1e-6} {b * 1e-6}"
    raw = get(SIA, params, limit=4 * 1024 * 1024)
    table = Table.read(io.BytesIO(raw), format="votable", use_names_over_ids=True)
    rows, seen = [], set()
    for row in table:

        def val(k):
            v = row[k] if k in table.colnames else None
            return None if v is None or getattr(v, "mask", False) else str(v)

        url = val("access_url")
        if not url or f"D{s['detector']}_" not in url:
            continue
        identity = val("obs_id") or val("obs_publisher_did") or url.split("/")[-1]
        if identity in seen:
            continue
        seen.add(identity)
        rows.append(
            {
                "id": identity,
                "url": url,
                "mjd": float(val("t_min")) if val("t_min") else None,
                "end_mjd": float(val("t_max")) if val("t_max") else None,
                "release": s["release"],
                "source": "SPHEREx",
                "detector": s["detector"],
                "band_min_m": val("em_min"),
                "band_max_m": val("em_max"),
            }
        )
    from science.geometry import time_summary

    selected = select_epochs(rows, s["max_frames"])
    return selected, {
        "returned_metadata": len(table),
        "metadata_limit": 100,
        "selection": "Up to 8 temporally spread observations including earliest/latest in bounded returned metadata",
        "selection_policy": "temporal-spread-v1",
        "returned_time_range": time_summary(rows),
        "selected_time_range": time_summary(selected),
        "possibly_truncated": len(table) >= 100,
        "coverage_warning": "The 100-row archive metadata sample may be truncated; its endpoints are not claimed to be the full archive baseline.",
        "endpoint": SIA,
    }


def neossat(s):
    radius = footprint_search_radius_deg(s["width"], s["height"])
    query = f"SELECT TOP 40 observationID, planeID, time_bounds_lower, time_bounds_upper, position_bounds, energy_bandpassName FROM caom2.Observation AS O JOIN caom2.Plane AS P ON O.obsID=P.obsID WHERE collection='NEOSSAT' AND INTERSECTS(CIRCLE('ICRS',{s['ra']},{s['dec']},{radius}),position_bounds)=1"
    raw = get(
        "https://ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/argus/sync",
        {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": query},
        limit=2 * 1024 * 1024,
    )
    table = Table.read(io.BytesIO(raw), format="ascii.csv")
    # Discovery is separate from calibrated SPHEREx imaging. Product URLs must be resolved from CADC artifact metadata.
    return [], {
        "returned_metadata": len(table),
        "observations": [{k: str(row[k]) for k in table.colnames} for row in table],
        "warning": "NEOSSat artifact retrieval/calibration is not yet validated; metadata only, no sky registration claimed.",
    }


def gaia(s):
    radius = footprint_search_radius_deg(s["width"], s["height"])
    query = f"SELECT TOP 200 source_id,ra,dec,ref_epoch,pmra,pmdec,parallax,radial_velocity,phot_g_mean_mag FROM gaiadr3.gaia_source WHERE 1=CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{s['ra']},{s['dec']},{radius}))"
    raw = get(
        "https://gea.esac.esa.int/tap-server/tap/sync",
        {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": query},
        limit=1024 * 1024,
    )
    table = Table.read(io.BytesIO(raw), format="ascii.csv")
    return {
        "release": "Gaia DR3",
        "table": "gaiadr3.gaia_source",
        "epoch": "J2016.0",
        "limit": 200,
        "propagated": False,
        "sources": [
            {k: None if getattr(row[k], "mask", False) else str(row[k]) for k in table.colnames} for row in table
        ],
    }


def wise(s):
    radius = footprint_search_radius_deg(s["width"], s["height"])
    query = (
        "SELECT TOP 200 designation,ra,dec,w1mpro,w2mpro,ph_qual,cc_flags "
        "FROM allwise_p3as_psd WHERE 1=CONTAINS("
        f"POINT('ICRS',ra,dec),CIRCLE('ICRS',{s['ra']},{s['dec']},{radius}))"
    )
    endpoint = "https://irsa.ipac.caltech.edu/TAP/sync"
    raw = get(endpoint, {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": query}, limit=1024 * 1024)
    table = Table.read(io.BytesIO(raw), format="ascii.csv")
    return {
        "release": "AllWISE Source Catalog", "table": "allwise_p3as_psd",
        "endpoint": endpoint, "limit": 200, "possibly_truncated": len(table) >= 200,
        "propagated": False,
        "warning": "Catalog positions are not propagated to the exposure epoch. W1/W2 magnitudes are not SPHEREx fluxes. No source association is established.",
        "sources": [{k: None if getattr(row[k], "mask", False) else str(row[k]) for k in table.colnames} for row in table],
    }


def resolve(name):
    if not name or len(name) > 120:
        raise ValueError("Object name must contain 1–120 characters")
    import xml.etree.ElementTree as ET
    from urllib.parse import quote

    # CDS explicitly recommends this mirror during the November 2026 Strasbourg outage.
    raw = get("https://vizier.idia.ac.za/viz-bin/nph-sesame/-oxp/SNV?" + quote(name, safe=""), limit=1024 * 1024)
    root = ET.fromstring(raw)
    if len(root.findall(".//Target")) > 1:
        raise ValueError("Object is unknown or ambiguous; enter explicit coordinates")
    resolvers = [r for r in root.findall(".//Resolver") if r.findtext("jradeg") and r.findtext("jdedeg")]
    if not resolvers:
        raise ValueError("Object is unknown or ambiguous; enter explicit coordinates")
    r = resolvers[0]
    try:
        ra, dec = float(r.findtext("jradeg")), float(r.findtext("jdedeg"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Resolver returned invalid coordinates") from exc
    if not math.isfinite(ra) or not math.isfinite(dec) or not 0 <= ra < 360 or not -90 <= dec <= 90:
        raise ValueError("Resolver returned invalid coordinates")
    return {
        "name": r.findtext("oname") or name,
        "ra": ra,
        "dec": dec,
        "unit": "deg",
        "resolver": "CDS Sesame / IDIA mirror: " + r.attrib.get("name", ""),
        "reference": r.findtext("refPos"),
        "pmra_mas_yr": r.findtext("pm/pmRA"),
        "pmdec_mas_yr": r.findtext("pm/pmDE"),
        "epoch": "J2000 reference coordinates; catalog position epoch not supplied by resolver. Proper motion not applied; not a current-position prediction.",
    }


def locate_hips_cube_tile(ra, dec, layer=62):
    import urllib.request

    import astropy.units as u
    from astropy_healpix import HEALPix

    hp = HEALPix(nside=32, order='nested', frame='icrs')
    try:
        ipix = int(hp.lonlat_to_healpix(float(ra) * u.deg, float(dec) * u.deg))
    except Exception as e:
        raise ValueError(f'Invalid celestial coordinates for HiPS indexing: {e}')

    dir_id = int((ipix // 10000) * 10000)
    base_url = 'https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/hips5_cube/hips_20261026'
    tile_url = f'{base_url}/Norder5/Dir{dir_id}/Npix{ipix}_cube.fits'

    # Check upstream availability with a bounded HTTP Range check
    req = urllib.request.Request(tile_url, headers={'Range': 'bytes=0-100', 'User-Agent': 'Argus/1.0'})
    available = False
    error_msg = None
    try:
        with urllib.request.urlopen(req, timeout=4) as r:
            available = (r.status in (200, 206))
    except Exception as exc:
        error_msg = str(exc)

    neighbors = [int(n) for n in hp.neighbours(ipix) if n >= 0]
    boundaries = hp.boundaries_lonlat(ipix, step=1)
    corners = [
        [float(boundaries[0][0, i].to_value(u.deg)), float(boundaries[1][0, i].to_value(u.deg))]
        for i in range(4)
    ]
    center = hp.healpix_to_lonlat(ipix)
    center_coords = [float(center[0].to_value(u.deg)), float(center[1].to_value(u.deg))]

    hips_png_base = 'https://irsa.ipac.caltech.edu/data/hips/SPHEREx/spherex_allsky_cube'
    neighbor_tiles = []
    for n in neighbors:
        ndir = int((n // 10000) * 10000)
        nb_boundaries = hp.boundaries_lonlat(n, step=1)
        nb_corners = [
            [float(nb_boundaries[0][0, i].to_value(u.deg)), float(nb_boundaries[1][0, i].to_value(u.deg))]
            for i in range(4)
        ]
        nb_center = hp.healpix_to_lonlat(n)
        local_nb_path = Path(f'static/hips_tiles/Npix{n}.png')
        nb_png_url = f'/static/hips_tiles/Npix{n}.png' if local_nb_path.exists() else f'{hips_png_base}/Norder5/Dir{ndir}/Npix{n}.png'
        neighbor_tiles.append({
            'ipix': n,
            'dir': ndir,
            'png_url': nb_png_url,
            'cube_url': f'{base_url}/Norder5/Dir{ndir}/Npix{n}_cube.fits',
            'center': [float(nb_center[0].to_value(u.deg)), float(nb_center[1].to_value(u.deg))],
            'corners': nb_corners,
        })

    local_tile_path = Path(f'static/hips_tiles/Npix{ipix}.png')
    tile_png_url = f'/static/hips_tiles/Npix{ipix}.png' if local_tile_path.exists() else f'{hips_png_base}/Norder5/Dir{dir_id}/Npix{ipix}.png'

    return {
        'ra': float(ra),
        'dec': float(dec),
        'order': 5,
        'ipix': ipix,
        'dir': dir_id,
        'tile_url': tile_url,
        'png_url': tile_png_url,
        'center': center_coords,
        'corners': corners,
        'layer': int(layer),
        'available': available,
        'error': error_msg,
        'neighbors': neighbors,
        'neighbor_tiles': neighbor_tiles,
        'spectral_resolution': '102 channels nominal across 0.75 - 5.0 um',
        'disclaimer': 'SPHEREx HiPS Mosaic product is an all-sky coadd. Spectral combination does not improve spatial angular resolution.',
    }
