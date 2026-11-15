"""Read genuine DR1 mosaic cube channels without inventing spectral metadata."""
import io

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS


def cube_info(path):
    with fits.open(path, memmap=False) as hdus:
        image = hdus['IMAGE'].data
        hits = hdus['NHITS'].data
        if image.shape != (102, 512, 512) or hits.shape != image.shape:
            raise ValueError('Expected a DR1 102 × 512 × 512 IMAGE/NHITS cube')
        if 'WCS-WAVE' not in hdus or not WCS(hdus['IMAGE'].header, hdus).has_celestial:
            raise ValueError('Missing or invalid complete cube WCS lookup')
        table = hdus['SPECTRAL_CHANNELS'].data
        if len(table) != 102 or 'WAVELENGTH' not in table.names:
            raise ValueError('Missing authoritative 102-channel wavelength table')
        wavelengths = np.asarray(table['WAVELENGTH'], dtype=float).ravel()
        if len(wavelengths) != 102 or not np.all(np.isfinite(wavelengths)):
            raise ValueError('Invalid channel wavelength metadata')
        valid = np.isfinite(image) & (hits > 0)
        return {
            'channels': [{'index': i, 'detector': int(table['DETECTOR'][i]), 'channel': int(table['SUBCHAN'][i]),
                          'wavelength_um': float(wavelengths[i]),
                          'bandwidth_um': float(table['BANDWIDTH'][i]),
                          'valid_fraction': float(valid[i].mean()),
                          'available': bool(valid[i].any())} for i in range(102)],
            'shape': list(image.shape), 'units': hdus['IMAGE'].header.get('BUNIT', 'not supplied'),
            'date_start': hdus[0].header.get('DATE-BEG'), 'date_end': hdus[0].header.get('DATE-END'),
            'warning': 'DR1 all-sky mosaic coadd, not a dated exposure. Valid means finite IMAGE and NHITS > 0; propagated flags are retained, not decoded into calibrated photometric validity. No molecular identification or quantitative uncertainty is inferred.',
        }


def channel_png(path, index, coverage=False, reference=None):
    from PIL import Image
    if not 0 <= index < 102:
        raise ValueError('Channel index must be 0–101')
    if reference is not None and not 0 <= reference < 102:
        raise ValueError('Reference channel index must be 0–101')
    with fits.open(path, memmap=False) as hdus:
        plane = np.asarray(hdus['IMAGE'].data[index], dtype=float)
        hits = hdus['NHITS'].data[index]
        valid = np.isfinite(plane) & (hits > 0)
        rgba = np.zeros((*plane.shape, 4), dtype=np.uint8)
        if coverage:
            rgba[valid] = [101, 226, 221, 255]
        elif valid.any():
            values = plane[valid]
            if reference is not None:
                other = hdus['IMAGE'].data[reference]
                other_valid = np.isfinite(other) & (hdus['NHITS'].data[reference] > 0)
                values = np.concatenate([values, other[other_valid]])
            low, high = np.percentile(values, [1, 99])
            norm = np.arcsinh(10 * np.clip((plane - low) / max(high-low, 1e-20), 0, 1)) / np.arcsinh(10)
            rgba[..., :3] = np.nan_to_num(norm[..., None] * 255).astype(np.uint8)
            rgba[..., 3] = valid * 255
        # FITS row zero is bottom; browser image row zero is top.
        out = io.BytesIO()
        Image.fromarray(rgba[::-1]).save(out, format='PNG')
        return out.getvalue()


def pixel_spectrum(path, x, y):
    if not (0 <= x < 512 and 0 <= y < 512):
        raise ValueError('Pixel outside cube tile')
    with fits.open(path, memmap=False) as hdus:
        wcs = WCS(hdus['IMAGE'].header, hdus).celestial
        ra, dec = wcs.pixel_to_world_values(x, y)
        waves = hdus['SPECTRAL_CHANNELS'].data['WAVELENGTH']
        points = []
        for index in range(102):
            value = float(hdus['IMAGE'].data[index, y, x])
            hits = int(hdus['NHITS'].data[index, y, x])
            flag = int(hdus['FLAGS'].data[index, y, x])
            valid = bool(np.isfinite(value) and hits > 0)
            points.append({'index': index, 'wavelength_um': float(waves[index]),
                           'surface_brightness': value if valid else None, 'nhits': hits,
                           'flags': flag, 'available': valid, 'uncertainty': None})
        return {'pixel': {'x': x, 'y': y}, 'coordinates': {'ra': float(ra), 'dec': float(dec)},
                'units': hdus['IMAGE'].header.get('BUNIT', 'not supplied'), 'measurements': points,
                'method': 'Single mosaic-pixel sampling of actual IMAGE/NHITS/FLAGS planes; no background subtraction or PSF fitting.',
                'warning': 'No propagated variance supplied by this product: uncertainty unavailable. This is a surface-brightness spectrum, not integrated point-source flux. No molecular identification.'}


def sky_spectrum(path, ra, dec):
    if not np.isfinite(ra) or not np.isfinite(dec) or not -90 <= dec <= 90 or not 0 <= ra < 360:
        raise ValueError('Finite ICRS coordinates required')
    with fits.open(path, memmap=False) as hdus:
        wcs = WCS(hdus['IMAGE'].header, hdus).celestial
        x, y = wcs.world_to_pixel_values(ra, dec)
        if not np.isfinite(x) or not np.isfinite(y):
            raise ValueError('Source is outside this cube tile')
        x, y = int(np.floor(x + 0.5)), int(np.floor(y + 0.5))
    result = pixel_spectrum(path, x, y)
    result['requested_coordinates'] = {'ra': ra, 'dec': dec}
    return result
