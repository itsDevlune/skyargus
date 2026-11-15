"""Extended science and numerical tests for coordinate grids, imaging, and stacking."""

import io

import numpy as np
import pytest
from PIL import Image

from science.coordinates import region
from science.imaging import grid, preview, weighted_stack


# ---------------------------------------------------------------------------
# Coordinate edge cases
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "ra,dec",
    [
        (0.0, 0.0),
        (180.0, 0.0),
        (0.001, 89.999),
        (359.999, -89.999),
        (90.0, 45.0),
        (270.0, -45.0),
    ],
)
def test_grid_roundtrip_edge_coordinates(ra, dec):
    w, shape = grid(region({"ra": ra, "dec": dec}))
    px = np.array([0.0, shape[1] / 2, shape[1] - 1])
    py = np.array([0.0, shape[0] / 2, shape[0] - 1])
    sky = w.pixel_to_world_values(px, py)
    x2, y2 = w.world_to_pixel_values(*sky)
    np.testing.assert_allclose(x2, px, atol=1e-6)
    np.testing.assert_allclose(y2, py, atol=1e-6)


def test_grid_center_pixel_matches_crval():
    """The center pixel of the grid should map to the requested coordinates."""
    ra, dec = 120.5, -30.2
    w, shape = grid(region({"ra": ra, "dec": dec}))
    cx, cy = (shape[1] - 1) / 2, (shape[0] - 1) / 2
    sky_ra, sky_dec = w.pixel_to_world_values(cx, cy)
    assert sky_ra == pytest.approx(ra, abs=0.01)
    assert sky_dec == pytest.approx(dec, abs=0.01)


# ---------------------------------------------------------------------------
# Rectangular FOV
# ---------------------------------------------------------------------------
def test_rectangular_fov_grid_shape():
    w_wide, shape_wide = grid(region({"ra": 10, "dec": 20, "width": 12, "height": 6}))
    assert shape_wide[1] > shape_wide[0], "Wide FOV should have more columns than rows"

    w_tall, shape_tall = grid(region({"ra": 10, "dec": 20, "width": 3, "height": 12}))
    assert shape_tall[0] > shape_tall[1], "Tall FOV should have more rows than columns"


def test_square_fov_produces_square_grid():
    _, shape = grid(region({"ra": 10, "dec": 20, "width": 6, "height": 6}))
    assert shape[0] == shape[1], "Square FOV should produce square grid"


def test_minimum_grid_dimension():
    """Even the smallest FOV should produce at least 10 pixels per axis."""
    _, shape = grid(region({"ra": 10, "dec": 20, "width": 1, "height": 1}))
    assert shape[0] >= 10
    assert shape[1] >= 10


# ---------------------------------------------------------------------------
# Weighted stack edge cases
# ---------------------------------------------------------------------------
def test_weighted_stack_single_frame():
    a = np.array([[[5.0, 3.0]]])
    v = np.array([[[2.0, 1.0]]])
    out, var, cov = weighted_stack(a, v)
    np.testing.assert_allclose(out, [[5.0, 3.0]])
    np.testing.assert_allclose(var, [[2.0, 1.0]])
    np.testing.assert_array_equal(cov, [[1, 1]])


def test_weighted_stack_all_nan():
    a = np.array([[[np.nan]], [[np.nan]]])
    v = np.array([[[1.0]], [[1.0]]])
    out, var, cov = weighted_stack(a, v)
    assert np.isnan(out[0, 0])
    np.testing.assert_array_equal(cov, [[0]])


def test_weighted_stack_zero_variance_excluded():
    a = np.array([[[5.0]], [[3.0]]])
    v = np.array([[[0.0]], [[1.0]]])
    out, var, cov = weighted_stack(a, v)
    np.testing.assert_allclose(out, [[3.0]])
    np.testing.assert_array_equal(cov, [[1]])


def test_weighted_stack_negative_variance_excluded():
    a = np.array([[[5.0]], [[3.0]]])
    v = np.array([[[-1.0]], [[1.0]]])
    out, var, cov = weighted_stack(a, v)
    np.testing.assert_allclose(out, [[3.0]])
    np.testing.assert_array_equal(cov, [[1]])


def test_weighted_stack_many_frames():
    rng = np.random.default_rng(42)
    n = 20
    truth = np.array([[10.0, 20.0, 30.0]])
    noise = rng.normal(0, 1, (n, 1, 3))
    arrays = truth + noise
    variances = np.ones_like(arrays)
    out, var, cov = weighted_stack(arrays, variances)
    np.testing.assert_allclose(out, truth, atol=0.5)
    np.testing.assert_array_equal(cov, [[n, n, n]])
    np.testing.assert_allclose(var, [[1 / n, 1 / n, 1 / n]])


def test_weighted_stack_shape_mismatch_rejected():
    a = np.array([[[1.0]]])
    v = np.array([[[1.0, 2.0]]])
    with pytest.raises(ValueError):
        weighted_stack(a, v)


def test_weighted_stack_2d_rejected():
    a = np.array([[1.0, 2.0]])
    v = np.array([[1.0, 1.0]])
    with pytest.raises(ValueError):
        weighted_stack(a, v)


# ---------------------------------------------------------------------------
# Preview rendering
# ---------------------------------------------------------------------------
def test_preview_all_nan():
    a = np.full((10, 10), np.nan)
    png = preview(a, 0, 1)
    img = np.asarray(Image.open(io.BytesIO(png)))
    assert (img[:, :, 3] == 0).all(), "All-NaN should produce fully transparent"


def test_preview_shape_matches_input():
    a = np.random.default_rng(0).random((20, 30))
    png = preview(a, 0, 1)
    img = Image.open(io.BytesIO(png))
    assert img.size == (30, 20), "Preview size should match (width, height) of input"


def test_preview_constant_array():
    """A constant array should produce a uniform grayscale preview."""
    a = np.full((15, 15), 5.0)
    png = preview(a, 0, 10)
    img = np.asarray(Image.open(io.BytesIO(png)))
    # All pixels should have the same R value and be fully opaque
    assert img[:, :, 3].min() == 255
    r_values = img[:, :, 0]
    assert r_values.std() == 0, "Constant input should produce uniform output"


def test_preview_returns_valid_png():
    a = np.random.default_rng(1).random((10, 10))
    png = preview(a, 0, 1)
    assert png[:8] == b"\x89PNG\r\n\x1a\n", "Output should start with PNG signature"


def test_preview_high_low_equal():
    """When low==high, preview should not crash (division by near-zero is handled)."""
    a = np.array([[5.0, 5.0], [5.0, 5.0]])
    png = preview(a, 5.0, 5.0)
    img = Image.open(io.BytesIO(png))
    assert img.size == (2, 2)
