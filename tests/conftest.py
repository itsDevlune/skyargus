"""Shared test fixtures for the Argus test suite."""

import pytest
from astropy.wcs import WCS

from apps.core.models import Sequence


@pytest.fixture
def sequence_with_frames():
    """A reusable sequence with 3 frames and celestial geometry."""
    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [29.5, 29.5]
    wcs.wcs.cdelt = [-6.2 / 3600, 6.2 / 3600]
    wcs.wcs.crval = [269.452, 4.693]
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    return Sequence.objects.create(
        cache_key="test-fixture-3frame",
        manifest={
            "schema_version": 1,
            "data_mode": "real",
            "frames": [
                {
                    "id": f"obs{i}",
                    "date": f"2025-08-{15 + i}T12:00:00",
                    "source": "SPHEREx",
                    "release": "dr1",
                    "units": "MJy / sr",
                    "preview": {"id": f"00000000-0000-0000-0000-00000000000{i}"},
                }
                for i in range(3)
            ],
            "warnings": ["test fixture"],
            "excluded": [],
            "geometry": {
                "mode": "celestial",
                "width": 58,
                "height": 58,
                "pixel_scale_arcsec": 6.2,
                "crval": [269.452, 4.693],
                "crpix": [29.5, 29.5],
                "cdelt": [-6.2 / 3600, 6.2 / 3600],
                "wcs": wcs.to_header().tostring(),
            },
            "selection": {
                "ra": 269.452,
                "dec": 4.693,
                "width": 6,
                "height": 6,
            },
        },
    )


@pytest.fixture
def native_sequence():
    """A NEOSSat native-detector sequence with no celestial WCS."""
    return Sequence.objects.create(
        cache_key="test-native-fixture",
        manifest={
            "schema_version": 1,
            "data_mode": "real",
            "frames": [
                {
                    "id": f"neo{i}",
                    "date": f"2025-09-{10 + i}T06:00:00",
                    "source": "NEOSSat",
                    "release": "CADC raw",
                    "units": "raw ADU (uncalibrated)",
                }
                for i in range(2)
            ],
            "warnings": ["native detector mode"],
            "excluded": [],
            "geometry": {
                "mode": "native",
                "width": 1024,
                "height": 1024,
            },
        },
    )
