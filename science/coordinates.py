import math

from astropy import units as u
from astropy.coordinates import Angle, SkyCoord


def footprint_search_radius_deg(width_arcmin, height_arcmin):
    """Radius of the circle enclosing a rectangular FOV, in degrees."""
    width, height = float(width_arcmin), float(height_arcmin)
    if not all(math.isfinite(value) and value > 0 for value in (width, height)):
        raise ValueError("FOV dimensions must be positive finite arcminutes")
    return math.hypot(width, height) / 120


def region(payload):
    unit = payload.get("unit", "deg")
    if unit not in ("deg", "hourangle"):
        raise ValueError("unit must be deg or hourangle (RA hours, Dec degrees)")
    ra, dec = payload.get("ra"), payload.get("dec")
    if ra is None or dec is None:
        raise ValueError("Explicit RA and Dec are required")
    if unit == "deg":
        ra, dec = float(ra), float(dec)
        if not all(map(math.isfinite, (ra, dec))) or not 0 <= ra < 360 or not -90 <= dec <= 90:
            raise ValueError("RA must be [0,360); Dec [-90,90], finite degrees")
    if unit == "hourangle":
        # Convert through the supplied hour unit before degrees: 24h may otherwise
        # round just below 360 degrees and incorrectly pass the upper bound.
        hour_value = Angle(ra, unit=u.hourangle).to_value(u.hourangle)
        angle, declination = Angle(ra, unit=u.hourangle), Angle(dec, unit=u.deg)
        if (
            not math.isfinite(angle.deg)
            or not 0 <= hour_value < 24
            or not math.isfinite(declination.deg)
            or not -90 <= declination.deg <= 90
        ):
            raise ValueError("RA hours must be [0,24); Dec [-90,90], finite")
    c = SkyCoord(ra, dec, unit=(u.hourangle if unit == "hourangle" else u.deg, u.deg))
    width, height = float(payload.get("width", 6)), float(payload.get("height", 6))
    if not all(math.isfinite(v) and 1 <= v <= 20 for v in (width, height)):
        raise ValueError("FOV width and height must be 1–20 arcminutes")
    source = payload.get("source", "spherex")
    if source not in ("spherex", "neossat"):
        raise ValueError("source must be spherex or neossat")
    release = payload.get("release", "dr1")
    if release not in ("dr1", "qr3"):
        raise ValueError("release must be dr1 or qr3")
    raw_detector = payload.get("detector", 1)
    detector = int(raw_detector)
    if isinstance(raw_detector, bool) or float(raw_detector) != detector:
        raise ValueError("detector must be an integer from 1 to 6")
    if detector not in range(1, 7):
        raise ValueError("detector must be 1–6")
    from datetime import date

    start, end = payload.get("start") or None, payload.get("end") or None
    if start:
        date.fromisoformat(start)
    if end:
        date.fromisoformat(end)
    if start and end and start > end:
        raise ValueError("Start date must precede end date")
    normalized = dict(
        ra=float(c.ra.deg),
        dec=float(c.dec.deg),
        unit="deg",
        width=width,
        height=height,
        source=source,
        release=release,
        detector=detector,
        start=start,
        end=end,
        max_frames=8,
        processing="argus-0.2-grid-v3-geometry-epochs"
        if source == "spherex"
        else "argus-0.1-native-v2-no-celestial-wcs",
    )
    if start or end:
        normalized["date_policy"] = "inclusive-utc-days-v1"
    return normalized
