import pytest

from science.motion import fit_motion


def test_motion_ra_wrap_and_cosine():
    p = [
        {"ra": 359.999, "dec": 60.0, "date": "2025-01-01T00:00:00"},
        {"ra": 0.001, "dec": 60.0, "date": "2025-01-02T00:00:00"},
    ]
    result = fit_motion(p, 1)
    assert result["east_arcsec_day"] == pytest.approx(3.6, abs=1e-6)
    assert result["component_error_arcsec_day"] == pytest.approx(2**0.5)


def test_no_baseline_rejected():
    with pytest.raises(ValueError):
        fit_motion([{"ra": 0, "dec": 0, "date": "2025-01-01"}] * 2, 1)
