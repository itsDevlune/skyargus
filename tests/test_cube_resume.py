import io
from unittest.mock import patch

import numpy as np
import pytest
from astropy.io import fits

from apps.core.cube_download import download_cube


def transfer_fixture():
    """Analytical transfer fixture only; never used as observation imagery."""
    out = io.BytesIO()
    fits.HDUList([
        fits.PrimaryHDU(), fits.ImageHDU(np.zeros((1, 1, 600000), dtype=np.float32), name='IMAGE'),
        fits.ImageHDU(name='NHITS'), fits.ImageHDU(name='FLAGS'),
        fits.BinTableHDU(name='SPECTRAL_CHANNELS'), fits.BinTableHDU(name='WCS-WAVE'),
    ]).writeto(out)
    return out.getvalue()


def test_resume_keeps_only_verified_complete_chunks(tmp_path):
    raw = transfer_fixture()
    def interrupted(url, **kwargs):
        start, end = kwargs['byte_range']
        if start >= 1048576 and end-start > 2880:
            raise TimeoutError('Controlled interrupted transfer')
        return raw[start:end+1]

    with patch('apps.core.cube_download.get', side_effect=interrupted):
        with pytest.raises(TimeoutError):
            download_cube('https://irsa.ipac.caltech.edu/fixture.fits', tmp_path)
    assert list(tmp_path.rglob('0-1048575.part'))
    calls = []
    def resumed(url, **kwargs):
        span = kwargs['byte_range']
        calls.append(span)
        return raw[span[0]:span[1]+1]
    with patch('apps.core.cube_download.get', side_effect=resumed):
        assert download_cube('https://irsa.ipac.caltech.edu/fixture.fits', tmp_path) == raw
    assert (0, 1048575) not in calls


def test_corrupt_cached_chunk_is_refetched(tmp_path):
    raw = transfer_fixture()
    def fetch(url, **kwargs):
        start, end = kwargs['byte_range']
        return raw[start:end+1]
    with patch('apps.core.cube_download.get', side_effect=fetch):
        download_cube('https://irsa.ipac.caltech.edu/fixture.fits', tmp_path)
    part = next(tmp_path.rglob('0-1048575.part'))
    part.write_bytes(b'x' * 1048576)
    with patch('apps.core.cube_download.get', side_effect=fetch) as request:
        assert download_cube('https://irsa.ipac.caltech.edu/fixture.fits', tmp_path) == raw
    assert any(call.kwargs['byte_range'] == (0, 1048575) for call in request.call_args_list)
