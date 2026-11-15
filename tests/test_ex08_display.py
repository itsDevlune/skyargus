import io
from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS
from PIL import Image

from science.coordinates import region
from science.imaging import preview, read_frame


def test_real_spherex_cutout_is_reprojected_to_north_up_east_left_grid():
    raw = (Path(__file__).parent / "fixtures/real/spherex-dr1-cutout.fits").read_bytes()
    selection = region({"ra": 269.452075, "dec": 4.693391, "width": 6, "height": 6})
    array, _, metadata = read_frame(raw, selection)
    wcs = WCS(fits.Header.fromstring(metadata["header"]))

    assert array.shape == (58, 58)
    assert metadata["coverage_fraction"] == 1
    np.testing.assert_allclose(wcs.wcs.crval, [selection["ra"], selection["dec"]], atol=1e-10)
    assert wcs.wcs.cdelt[0] < 0  # East is left.
    assert wcs.wcs.cdelt[1] > 0  # North is up.
    assert abs(wcs.wcs.cdelt[0]) * 3600 == pytest.approx(6.2)


def test_partial_wcs_coverage_stays_blank_in_reprojection_and_preview():
    # Small algorithm fixture: 4x4 native image covers only the center of the requested 1x1 arcmin grid.
    source_wcs = WCS(naxis=2)
    source_wcs.wcs.crpix = [2.5, 2.5]
    source_wcs.wcs.cdelt = [6.2 / 3600, 6.2 / 3600]  # Native east-right; display grid is east-left.
    source_wcs.wcs.crval = [10, 20]
    source_wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    values = np.tile(np.arange(4, dtype=np.float32), (4, 1))
    primary = fits.PrimaryHDU()
    image = fits.ImageHDU(values, header=source_wcs.to_header(), name="IMAGE")
    image.header["BUNIT"] = "test units"
    buffer = io.BytesIO()
    fits.HDUList([primary, image]).writeto(buffer)

    array, _, metadata = read_frame(buffer.getvalue(), region({"ra": 10, "dec": 20, "width": 1, "height": 1}))
    center_row = array[array.shape[0] // 2]
    covered = center_row[np.isfinite(center_row)]

    assert 0 < metadata["coverage_fraction"] < 1
    assert np.isnan(array).any()
    assert covered.size >= 2
    assert covered[0] > covered[-1]  # Target grid reverses native east-right orientation.
    rgba = np.asarray(Image.open(io.BytesIO(preview(array, 0, 3))))
    np.testing.assert_array_equal(rgba[..., 3] == 0, ~np.isfinite(array))
