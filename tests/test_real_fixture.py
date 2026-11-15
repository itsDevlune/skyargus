import hashlib
import json
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from science.coordinates import region
from science.imaging import read_frame


def test_real_fits_identity_wcs_wavelength_and_flags():
    root = Path(__file__).parent / "fixtures" / "real"
    raw = (root / "spherex-dr1-cutout.fits").read_bytes()
    meta = json.loads((root / "provenance.json").read_text())
    assert hashlib.sha256(raw).hexdigest() == meta["sha256"]
    s = region({"ra": 269.452075, "dec": 4.693391, "detector": 3})
    array, flags, result = read_frame(raw, s)
    assert np.isfinite(array).any()
    assert result["units"] == "MJy / sr"
    assert result["date"].startswith("2025-08-15")
    assert any(f["name"] == "SOURCE" and f["category"] == "informational" for f in result["decoded_flags"])
    # Independent FITS WCS-TAB evaluation (without irrelevant celestial SIP) verifies lookup offsets.
    import io

    with fits.open(io.BytesIO(raw)) as h:
        celestial = WCS(h["IMAGE"].header, h).celestial
        px, py = celestial.world_to_pixel_values(s["ra"], s["dec"])
        wave = WCS(h["IMAGE"].header, h, key="W")
        wave.sip = None
        expected = wave.pixel_to_world_values(px, py)
    np.testing.assert_allclose(result["wavelength"], expected, atol=1e-6)
    assert flags.shape == array.shape
