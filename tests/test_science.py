import io

import numpy as np
import pytest
from PIL import Image

from science.coordinates import region
from science.imaging import grid, preview, weighted_stack


@pytest.mark.parametrize("ra,dec", [(float("nan"), 1), (360, 1), (-1, 0), (0, 91), (0, float("inf"))])
def test_invalid_coordinates(ra, dec):
    with pytest.raises(ValueError):
        region({"ra": ra, "dec": dec})


def test_sexagesimal_and_limits():
    s = region({"ra": "08:55:10.831", "dec": "-07:14:42.53", "unit": "hourangle"})
    assert s["ra"] == pytest.approx(133.79512917)
    assert s["dec"] == pytest.approx(-7.24514722)
    with pytest.raises(ValueError):
        region({"ra": 1, "dec": 2, "width": 1000})


@pytest.mark.parametrize("ra,dec", [(359.99, 89.9), (0.01, -89.9), (269.45, 4.6)])
def test_grid_roundtrip(ra, dec):
    w, shape = grid(region({"ra": ra, "dec": dec}))
    px = np.array([0.0, shape[1] / 2, shape[1] - 1])
    py = np.array([0.0, shape[0] / 2, shape[0] - 1])
    sky = w.pixel_to_world_values(px, py)
    x, y = w.world_to_pixel_values(*sky)
    np.testing.assert_allclose(x, px, atol=1e-7)
    np.testing.assert_allclose(y, py, atol=1e-7)


def test_preview_vertical_orientation_and_mask():
    a = np.array([[0.0, np.nan], [10.0, 5.0]])
    image = np.asarray(Image.open(io.BytesIO(preview(a, 0, 10))))
    assert image[0, 0, 0] == 255
    assert image[1, 0, 0] == 0
    assert image[1, 1, 3] == 0


def test_weighted_known_result():
    arrays = np.array([[[2.0, np.nan]], [[6.0, 4.0]]])
    variances = np.array([[[1.0, 1.0]], [[3.0, 2.0]]])
    out, variance, coverage = weighted_stack(arrays, variances)
    np.testing.assert_allclose(out, [[3.0, 4.0]])
    np.testing.assert_allclose(variance, [[0.75, 2.0]])
    np.testing.assert_array_equal(coverage, [[2, 1]])
