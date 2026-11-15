import io

import numpy as np
import pytest
from astropy.io import fits

from science.cubes import channel_png, cube_info, pixel_spectrum, sky_spectrum


def test_cube_rejects_non_102_plane_inputs():
    buffer = io.BytesIO()
    fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(np.ones((2, 4, 4)), name='IMAGE'),
                  fits.ImageHDU(np.ones((2, 4, 4)), name='NHITS')]).writeto(buffer)
    buffer.seek(0)
    with pytest.raises(ValueError, match='102'):
        cube_info(buffer)


@pytest.mark.parametrize('index', [-1, 102])
def test_invalid_plane_rejected_before_file_access(index):
    with pytest.raises(ValueError, match='0–101'):
        channel_png('nonexistent', index)


@pytest.mark.parametrize('point', [(-1, 0), (0, 512)])
def test_spectrum_pixel_outside_tile_rejected(point):
    with pytest.raises(ValueError, match='outside'):
        pixel_spectrum('nonexistent', *point)


@pytest.mark.parametrize('coordinates', [(float('nan'), 0), (0, float('inf')), (-1, 0), (360, 0), (0, 91)])
def test_sky_spectrum_rejects_invalid_coordinates(coordinates):
    with pytest.raises(ValueError, match='ICRS'):
        sky_spectrum('nonexistent', *coordinates)


@pytest.mark.django_db
def test_cube_endpoint_invalid_coordinates(client):
    assert client.post('/api/v1/cubes', {'ra': 1, 'dec': 91}, content_type='application/json').status_code == 400


@pytest.mark.django_db
def test_cube_rejects_neossat(client):
    response = client.post('/api/v1/cubes', {'ra': 1, 'dec': 20, 'source': 'neossat'}, content_type='application/json')
    assert response.status_code == 400
