"""Independent numerical reference checks and real-data comparisons for scientific workflows."""

import numpy as np
import pytest

from science.analysis import (
    ARCSEC2_TO_SR,
)
from science.imaging import weighted_stack


def test_analytical_weighted_stack_accuracy():
    """Verify that weighted_stack mathematically solves the maximum likelihood estimate.

    For uncorrelated Gaussians y_i ~ N(mu, sigma_i^2), the minimum variance unbiased estimator is:
    mu_hat = sum(y_i / sigma_i^2) / sum(1 / sigma_i^2)
    Var(mu_hat) = 1 / sum(1 / sigma_i^2)
    """
    # 3 independent measurements with known values and variances
    values = np.array([[[10.0, 50.0]], [[12.0, 52.0]], [[14.0, 54.0]]])
    variances = np.array([[[1.0, 4.0]], [[2.0, 4.0]], [[4.0, 4.0]]])

    out_val, out_var, count = weighted_stack(values, variances)

    # Pixel (0, 0):
    # w = [1.0, 0.5, 0.25], sum(w) = 1.75
    # y = (10*1.0 + 12*0.5 + 14*0.25) / 1.75 = 19.5 / 1.75 = 11.142857
    # var = 1 / 1.75 = 0.57142857
    assert np.isclose(out_val[0, 0], 19.5 / 1.75, atol=1e-8)
    assert np.isclose(out_var[0, 0], 1.0 / 1.75, atol=1e-8)
    assert count[0, 0] == 3

    # Pixel (0, 1): equal variances = 4.0 -> unweighted average
    # w = [0.25, 0.25, 0.25], sum(w) = 0.75
    # y = (50 + 52 + 54) / 3 = 52.0
    # var = 1 / 0.75 = 1.33333333 = sigma^2 / N = 4 / 3
    assert np.isclose(out_val[0, 1], 52.0, atol=1e-8)
    assert np.isclose(out_var[0, 1], 4.0 / 3.0, atol=1e-8)
    assert count[0, 1] == 3


def test_weighted_stack_handles_nan_and_zero_variance():
    """Verify quality masking: nonfinite values and nonpositive variances must be excluded."""
    values = np.array([[[10.0]], [[np.nan]], [[20.0]]])
    variances = np.array([[[1.0]], [[1.0]], [[0.0]]])  # second is NaN, third has var=0 (invalid)

    out_val, out_var, count = weighted_stack(values, variances)
    # Only measurement 0 is valid
    assert np.isclose(out_val[0, 0], 10.0)
    assert np.isclose(out_var[0, 0], 1.0)
    assert count[0, 0] == 1


def test_photometric_solid_angle_unit_conversion():
    """Verify solid angle conversion from MJy/sr to mJy.

    1 sr = (180 * 3600 / pi)^2 arcsec^2 ~ 4.2545e10 arcsec^2.
    For a 6.2" x 6.2" pixel:
    omega_pix = (6.2 * 6.2) * (pi / (180*3600))^2 sr ~ 9.035e-10 sr.
    1 MJy/sr = 10^9 mJy / sr.
    Flux in 1 pixel of 1.0 MJy/sr = 10^9 * omega_pix mJy ~ 0.9035 mJy.
    """
    pixscale_arcsec = 6.2
    omega_pix = (pixscale_arcsec**2) * ARCSEC2_TO_SR
    mJy_per_MJy_sr = 1e9 * omega_pix
    assert 0.90 < mJy_per_MJy_sr < 0.91


@pytest.mark.django_db
def test_hips_cube_endpoint_validation(client):
    """Test HiPS mosaic endpoint coordinate bounds, layer boundaries and tile lookup."""
    # 1. Valid coordinate lookup
    resp = client.get("/api/v1/hips/cube?ra=60.811&dec=51.340&layer=62")
    assert resp.status_code == 200
    data = resp.json()
    assert data["order"] == 5
    assert data["ipix"] == 445
    assert data["layer"] == 62
    assert "tile_url" in data
    assert "neighbors" in data
    assert len(data["neighbors"]) > 0

    # 2. Out of bounds Dec
    bad_dec = client.get("/api/v1/hips/cube?ra=60.811&dec=95.0")
    assert bad_dec.status_code == 400
    assert "Declination" in bad_dec.json()["error"]["message"]

    # 3. Out of bounds layer
    bad_layer = client.get("/api/v1/hips/cube?ra=60.811&dec=0.0&layer=105")
    assert bad_layer.status_code == 400
    assert "layer" in bad_layer.json()["error"]["message"]
