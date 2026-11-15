import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time


def fit_motion(points, position_error_arcsec):
    if not 0 < position_error_arcsec <= 60 or len(points) < 2:
        raise ValueError("At least two dated marks and a stated positional error (0–60 arcsec) required")
    coords = SkyCoord([p["ra"] for p in points], [p["dec"] for p in points], unit="deg")
    times = Time([p["date"] for p in points], scale="utc")
    t = times.jd - times.jd.min()
    if np.ptp(t) <= 0:
        raise ValueError("Distinct observation times required")
    if coords[0].separation(coords).max() > 1 * u.deg:
        raise ValueError("Motion tangent-plane fit is limited to a 1 degree field")
    x, y = coords[0].spherical_offsets_to(coords)
    matrix = np.column_stack([np.ones(len(t)), t])
    bx = np.linalg.lstsq(matrix, x.arcsec, rcond=None)[0]
    by = np.linalg.lstsq(matrix, y.arcsec, rcond=None)[0]
    covariance = position_error_arcsec**2 * np.linalg.inv(matrix.T @ matrix)
    residual = np.hypot(x.arcsec - matrix @ bx, y.arcsec - matrix @ by)
    return {
        "method": "Unweighted tangent-offset linear least squares with supplied independent isotropic positional error",
        "east_arcsec_day": float(bx[1]),
        "north_arcsec_day": float(by[1]),
        "component_error_arcsec_day": float(np.sqrt(covariance[1, 1])),
        "baseline_days": float(np.ptp(t)),
        "rms_arcsec": float(np.sqrt(np.mean(residual**2))),
        "points": points,
        "warning": "Manual associations may identify different sources. Assumed positional errors are not measured astrometric uncertainty. No orbit, distance or hazard inference.",
    }
