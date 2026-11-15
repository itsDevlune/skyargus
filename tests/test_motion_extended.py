"""Extended motion fitting tests covering edge cases and known results."""

import pytest

from science.motion import fit_motion


def test_motion_zero_motion():
    """Stationary points should yield near-zero rates."""
    p = [
        {"ra": 180.0, "dec": 45.0, "date": "2025-01-01T00:00:00"},
        {"ra": 180.0, "dec": 45.0, "date": "2025-01-10T00:00:00"},
    ]
    r = fit_motion(p, 1.0)
    assert abs(r["east_arcsec_day"]) < 0.01
    assert abs(r["north_arcsec_day"]) < 0.01
    assert r["baseline_days"] == pytest.approx(9.0)
    assert r["rms_arcsec"] < 0.01


def test_motion_north_only():
    """Pure north motion with RA constant."""
    p = [
        {"ra": 100.0, "dec": 30.0, "date": "2025-01-01T00:00:00"},
        {"ra": 100.0, "dec": 30.001, "date": "2025-01-02T00:00:00"},  # +3.6″
    ]
    r = fit_motion(p, 1.0)
    assert abs(r["east_arcsec_day"]) < 0.5
    assert r["north_arcsec_day"] == pytest.approx(3.6, abs=0.1)


def test_motion_three_points():
    """Three equally-spaced points at known east rate."""
    p = [
        {"ra": 50.0, "dec": 0.0, "date": "2025-01-01T00:00:00"},
        {"ra": 50.001, "dec": 0.0, "date": "2025-01-02T00:00:00"},
        {"ra": 50.002, "dec": 0.0, "date": "2025-01-03T00:00:00"},
    ]
    r = fit_motion(p, 1.0)
    assert r["east_arcsec_day"] == pytest.approx(3.6, abs=0.1)
    assert r["baseline_days"] == pytest.approx(2.0)


def test_motion_error_must_be_positive():
    p = [
        {"ra": 0, "dec": 0, "date": "2025-01-01"},
        {"ra": 1, "dec": 0, "date": "2025-01-02"},
    ]
    with pytest.raises(ValueError):
        fit_motion(p, 0)
    with pytest.raises(ValueError):
        fit_motion(p, -1)


def test_motion_error_must_not_exceed_60():
    p = [
        {"ra": 0, "dec": 0, "date": "2025-01-01"},
        {"ra": 0.001, "dec": 0, "date": "2025-01-02"},
    ]
    with pytest.raises(ValueError):
        fit_motion(p, 61)


def test_motion_field_too_large():
    p = [
        {"ra": 0, "dec": 0, "date": "2025-01-01"},
        {"ra": 2, "dec": 0, "date": "2025-01-02"},
    ]
    with pytest.raises(ValueError, match="1 degree"):
        fit_motion(p, 1)


def test_motion_single_point_rejected():
    with pytest.raises(ValueError):
        fit_motion([{"ra": 0, "dec": 0, "date": "2025-01-01"}], 1)


def test_motion_empty_list_rejected():
    with pytest.raises(ValueError):
        fit_motion([], 1)


def test_motion_result_contains_warning():
    p = [
        {"ra": 180.0, "dec": 0.0, "date": "2025-01-01T00:00:00"},
        {"ra": 180.001, "dec": 0.0, "date": "2025-01-02T00:00:00"},
    ]
    r = fit_motion(p, 1.0)
    assert "warning" in r
    assert "manual" in r["warning"].lower() or "Manual" in r["warning"]


def test_motion_result_contains_method():
    p = [
        {"ra": 180.0, "dec": 0.0, "date": "2025-01-01T00:00:00"},
        {"ra": 180.001, "dec": 0.0, "date": "2025-01-02T00:00:00"},
    ]
    r = fit_motion(p, 1.0)
    assert "method" in r
    assert "least squares" in r["method"].lower()


def test_motion_uncertainty_decreases_with_more_points():
    """More observations should reduce uncertainty, all else equal."""
    base = [
        {"ra": 100.0 + i * 0.001, "dec": 30.0, "date": f"2025-01-{1 + i:02d}T00:00:00"} for i in range(10)
    ]
    r2 = fit_motion(base[:2], 1.0)
    r5 = fit_motion(base[:5], 1.0)
    r10 = fit_motion(base, 1.0)
    assert r10["component_error_arcsec_day"] < r5["component_error_arcsec_day"]
    assert r5["component_error_arcsec_day"] < r2["component_error_arcsec_day"]


def test_motion_near_pole():
    """Motion near the celestial pole where RA cosine matters."""
    p = [
        {"ra": 0.0, "dec": 89.0, "date": "2025-01-01T00:00:00"},
        {"ra": 1.0, "dec": 89.0, "date": "2025-01-02T00:00:00"},
    ]
    r = fit_motion(p, 1.0)
    # Near the pole, 1° of RA is much less than 3600″ east because of cos(dec)
    assert abs(r["east_arcsec_day"]) < 100  # Would be ~62.8″ at dec=89°
