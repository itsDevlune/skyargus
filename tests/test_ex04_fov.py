import pytest

from science.coordinates import footprint_search_radius_deg, region


@pytest.mark.parametrize("width,height", [(1, 1), (20, 20), (1, 20), (7.5, 12)])
def test_fov_custom_dimensions_keep_full_width_and_height_arcminutes(width, height):
    selection = region({"ra": 180, "dec": 0, "width": width, "height": height})

    assert selection["width"] == width
    assert selection["height"] == height


@pytest.mark.parametrize(
    "width,height",
    [(0, 6), (-1, 6), (20.01, 6), (6, 0.99), (float("nan"), 6), (6, float("inf"))],
)
def test_fov_custom_dimensions_reject_out_of_bounds_or_nonfinite_values(width, height):
    with pytest.raises(ValueError, match="FOV width and height"):
        region({"ra": 180, "dec": 0, "width": width, "height": height})


def test_rectangular_fov_search_radius_is_half_diagonal_not_half_width():
    # A 6 × 8 arcmin field needs a 5 arcmin enclosing radius, not 3 arcmin.
    assert footprint_search_radius_deg(6, 8) == pytest.approx(5 / 60)
    assert footprint_search_radius_deg(6, 8) > 6 / 120


@pytest.mark.parametrize("width,height", [(0, 6), (float("nan"), 6), (6, float("inf"))])
def test_fov_search_radius_rejects_invalid_dimensions(width, height):
    with pytest.raises(ValueError, match="positive finite"):
        footprint_search_radius_deg(width, height)

