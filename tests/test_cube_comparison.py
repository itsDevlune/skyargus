import io

import numpy as np
from astropy.io import fits
from PIL import Image

from science.cubes import channel_png


def test_compared_channels_share_numeric_stretch_and_preserve_coverage(tmp_path):
    # Analytical fixture only, not used in the user-facing archive viewer.
    image = np.full((102, 2, 2), np.nan, dtype=np.float32)
    image[0] = [[0, 1], [2, 3]]
    image[1] = [[10, 11], [12, 13]]
    hits = np.ones_like(image, dtype=np.int16)
    hits[0, 0, 0] = 0
    path = tmp_path / 'comparison.fits'
    fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(image, name='IMAGE'), fits.ImageHDU(hits, name='NHITS')]).writeto(path)
    a = np.array(Image.open(io.BytesIO(channel_png(path, 0, reference=1))))
    b = np.array(Image.open(io.BytesIO(channel_png(path, 1, reference=0))))
    assert a[..., 0].max() < b[..., 0].min()
    assert a[1, 0, 3] == 0  # FITS row zero maps to bottom PNG row.
    assert b[..., 3].min() == 255
