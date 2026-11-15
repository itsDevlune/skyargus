import io
from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales

from apps.core.providers import select_epochs
from science.coordinates import region
from science.geometry import bandpass_comparison, footprint, inspect_manifest, output_geometry
from science.imaging import grid, read_frame


@pytest.mark.parametrize("width,height,expected", [(6, 6, (58, 58)), (12, 12, (116, 116)), (12, 6, (58, 116))])
def test_requested_arcminutes_match_actual_wcs(width, height, expected):
    s = region({"ra": 74.08667, "dec": -66.53694, "width": width, "height": height})
    w, shape = grid(s)
    assert shape == expected
    header = w.to_header()
    actual = WCS(header)
    measured = output_geometry(actual, shape)
    assert measured["width_arcmin"] == pytest.approx(width, abs=0.06)
    assert measured["height_arcmin"] == pytest.approx(height, abs=0.06)
    np.testing.assert_allclose(proj_plane_pixel_scales(actual) * 3600, [6.2, 6.2], atol=1e-8)


def test_real_fits_12_arcmin_grid_and_coverage_are_not_58_pixels():
    raw = (Path(__file__).parent / "fixtures/real/spherex-dr1-cutout.fits").read_bytes()
    s = region({"ra": 269.452075, "dec": 4.693391, "width": 12, "height": 12, "detector": 3})
    arr, flags, meta = read_frame(raw, s)
    assert arr.shape == (116, 116)
    output = WCS(fits.Header.fromstring(meta["header"]))
    extent = footprint(output, arr.shape)
    assert extent["width_arcmin"] == pytest.approx(12, abs=0.06)
    assert 0 < meta["coverage_fraction"] < 1
    assert meta["coverage_fraction"] == pytest.approx(np.isfinite(arr).mean())
    with fits.open(io.BytesIO(raw)) as h:
        native_wcs = WCS(h["IMAGE"].header, h).celestial
        returned = footprint(native_wcs, h["IMAGE"].data.shape)
    assert meta["returned_footprint"]["width_arcmin"] == pytest.approx(returned["width_arcmin"])
    assert meta["valid_data"]["bounding_footprint"] is not None


def test_old_cached_six_arcminute_data_is_not_described_as_twelve():
    s = region({"ra": 1, "dec": 2, "width": 6, "height": 6})
    w, shape = grid(s)
    manifest = {
        "selection": {**s, "width": 12, "height": 12},
        "geometry": {"width": shape[1], "height": shape[0], "wcs": w.to_header().tostring()},
        "frames": [],
    }
    inspected = inspect_manifest(manifest)
    assert inspected["inspection"]["request_grid_consistent"] is False
    assert inspected["inspection"]["output"]["width_arcmin"] < 6.01
    assert "inspection" not in manifest  # read-time enrichment never rewrites reports/cache


def test_epoch_selection_includes_baseline_not_only_dense_early_visits():
    times = [60000 + i / 1000 for i in range(90)] + [60100, 60200, 60300, 60400, 60500]
    rows = [{"id": str(i), "mjd": t} for i, t in enumerate(times)]
    selected = select_epochs(rows, 8)
    assert len(selected) == 8
    assert selected[0]["mjd"] == 60000
    assert selected[-1]["mjd"] == 60500
    assert len([r for r in selected if r["mjd"] >= 60100]) >= 5
    assert len({r["id"] for r in selected}) == 8


def test_wavelength_diagnostic_does_not_claim_calibrated_comparability():
    a = {"wavelength": [1.0, 0.1]}
    result = bandpass_comparison(a, {"wavelength": [1.02, 0.1]})
    assert result["overlap_fraction"] == pytest.approx(0.8)
    assert "not established" in result["reason"]
    assert bandpass_comparison(a, {"wavelength": [2.0, 0.1]})["status"] == "disjoint_display_bandpasses"
    assert bandpass_comparison(a, {"wavelength": None})["status"] == "not_assessed"
