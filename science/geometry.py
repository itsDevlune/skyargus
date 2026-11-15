"""Geometry and comparison diagnostics derived from WCS, never UI labels."""

import copy
import math

from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales


def footprint(wcs, shape, bounds=None):
    ny, nx = shape
    left, bottom, right, top = bounds or (-0.5, -0.5, nx - 0.5, ny - 0.5)
    xs = [left, right, right, left]
    ys = [bottom, bottom, top, top]
    ra, dec = wcs.pixel_to_world_values(xs, ys)
    midx, midy = (left + right) / 2, (bottom + top) / 2
    a = wcs.pixel_to_world(left, midy)
    b = wcs.pixel_to_world(right, midy)
    c = wcs.pixel_to_world(midx, bottom)
    d = wcs.pixel_to_world(midx, top)
    return {
        "corners_icrs_deg": [[float(r), float(d)] for r, d in zip(ra, dec)],
        "width_arcmin": float(a.separation(b).arcmin),
        "height_arcmin": float(c.separation(d).arcmin),
        "definition": "Spherical edge-midpoint separations; corners at pixel edges",
    }


def output_geometry(wcs, shape):
    scale = proj_plane_pixel_scales(wcs) * 3600
    return {
        "pixels": [int(shape[1]), int(shape[0])],
        "pixel_scale_arcsec": [float(abs(scale[0])), float(abs(scale[1]))],
        **footprint(wcs, shape),
    }


def time_summary(frames):
    from astropy.time import Time

    dates = []
    for f in frames:
        try:
            t = float(f["mjd"]) if f.get("mjd") is not None else float(Time(f["date"], scale="utc").mjd)
            if math.isfinite(t):
                dates.append(t)
        except (KeyError, TypeError, ValueError):
            continue
    if not dates:
        return {"first": None, "last": None, "baseline_days": None, "distinct_epochs": 0}
    return {
        "first": Time(min(dates), format="mjd").isot,
        "last": Time(max(dates), format="mjd").isot,
        "baseline_days": max(dates) - min(dates),
        "distinct_epochs": len(set(dates)),
    }


def bandpass_comparison(a, b):
    wa, wb = a.get("wavelength"), b.get("wavelength")
    if not wa or not wb or not all(math.isfinite(v) and v > 0 for v in [*wa, *wb]):
        return {
            "status": "not_assessed",
            "overlap_fraction": None,
            "reason": "Position-dependent visualization wavelength/bandwidth unavailable",
        }
    low, high = max(wa[0] - wa[1] / 2, wb[0] - wb[1] / 2), min(wa[0] + wa[1] / 2, wb[0] + wb[1] / 2)
    overlap = max(0.0, high - low) / min(wa[1], wb[1])
    return {
        "status": "overlapping_display_bandpasses" if overlap > 0 else "disjoint_display_bandpasses",
        "overlap_fraction": float(min(1.0, overlap)),
        "center_difference_um": abs(wa[0] - wb[0]),
        "reason": "Field-center visualization lookup only; calibrated response, PSF and alignment matching not established",
    }


def inspect_manifest(manifest):
    """Read-time diagnostics enrich old caches without rewriting pinned evidence."""
    m = copy.deepcopy(manifest)
    s = m.get("selection", {})
    geometry = m.get("geometry", {})
    inspection = {
        "requested": {
            "width_arcmin": s.get("width"),
            "height_arcmin": s.get("height"),
            "unit": "arcmin",
            "definition": "Full requested width and height, not cone radius",
        },
        "time": time_summary(m.get("frames", [])),
        "comparison_warning": "Same detector is not proof of spectral comparability.",
    }
    if all(s.get(k) is not None for k in ("width", "height", "ra", "dec")):
        nominal = WCS(naxis=2)
        nominal.wcs.crpix = [1.5, 1.5]
        nominal.wcs.cdelt = [-s["width"] / 120, s["height"] / 120]
        nominal.wcs.crval = [s["ra"], s["dec"]]
        nominal.wcs.ctype = ["RA---TAN", "DEC--TAN"]
        inspection["requested"]["corners_icrs_deg"] = footprint(nominal, (2, 2))["corners_icrs_deg"]
    if geometry.get("mode") == "native":
        inspection["output"] = {
            "pixels": [geometry.get("width"), geometry.get("height")],
            "definition": "Native detector crop; requested sky FOV is discovery only; celestial footprint not assessed",
        }
    elif geometry.get("wcs"):
        w = WCS(fits.Header.fromstring(geometry["wcs"])).celestial
        shape = (geometry["height"], geometry["width"])
        inspection["output"] = output_geometry(w, shape)
        requested = [s.get("width"), s.get("height")]
        actual = [inspection["output"]["width_arcmin"], inspection["output"]["height_arcmin"]]
        tolerance = max(inspection["output"]["pixel_scale_arcsec"]) / 60
        inspection["request_grid_consistent"] = all(
            r is not None and abs(r - a) <= tolerance for r, a in zip(requested, actual)
        )
    else:
        inspection["output"] = {"definition": "WCS geometry unavailable; not assessed"}
    m["inspection"] = inspection
    return m
