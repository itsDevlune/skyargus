"""Surface-brightness display reprojection. Quantitative products require separate validation."""

import hashlib
import io
import os
import uuid

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from PIL import Image
from reproject import reproject_interp
from scipy.interpolate import RegularGridInterpolator


def grid(s):
    scale = 6.2 / 3600
    nx, ny = max(10, round(s["width"] / 60 / scale)), max(10, round(s["height"] / 60 / scale))
    w = WCS(naxis=2)
    w.wcs.crpix = [(nx + 1) / 2, (ny + 1) / 2]
    w.wcs.cdelt = [-scale, scale]
    w.wcs.crval = [s["ra"], s["dec"]]
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    return w, (ny, nx)


def read_frame(raw, s):
    if raw[:6] != b"SIMPLE":
        raise ValueError("Expected an uncompressed FITS product")
    with fits.open(io.BytesIO(raw), memmap=False, lazy_load_hdus=False) as hdus:
        if "IMAGE" not in hdus:
            raise ValueError("Missing IMAGE HDU")
        hdu = hdus["IMAGE"]
        if hdu.header.get("NAXIS1", 0) * hdu.header.get("NAXIS2", 0) > 1024 * 1024:
            raise ValueError("Cutout pixel budget exceeded")
        native = np.asarray(hdu.data, dtype=float)
        native_wcs = WCS(hdu.header, hdus).celestial
        if not native_wcs.has_celestial:
            raise ValueError("No usable celestial WCS")
        target, shape = grid(s)
        arr, footprint = reproject_interp((native, native_wcs), target, shape_out=shape)
        valid = (footprint > 0) & np.isfinite(arr)
        arr[~valid] = np.nan
        flags = None
        decoded_flags = []
        if "FLAGS" in hdus:
            flags, _ = reproject_interp(
                (hdus["FLAGS"].data.astype(float), native_wcs), target, shape_out=shape, order="nearest-neighbor"
            )
            flag_header = hdus["FLAGS"].header
            invalid = {
                "SUR_ERROR",
                "NONFUNC",
                "MISSING_DATA",
                "HOT",
                "COLD",
                "NONLINEAR",
                "PERSIST",
                "BLOOM",
                "SNOWBALL",
                "HALO",
                "SATELLITE_HALO",
            }
            informational = {"SOURCE", "FULLSAMPLE"}
            for key in flag_header:
                if key.startswith("MSKN"):
                    suffix = key[4:]
                    name = str(flag_header[key]).strip()
                    mask = int(flag_header.get("MSKM" + suffix, 0))
                    finite_flags = flags[np.isfinite(flags)].astype("uint32")
                    decoded_flags.append(
                        {
                            "name": name,
                            "bitmask": mask,
                            "description": flag_header.get("MSKD" + suffix),
                            "category": "invalid_for_photometry"
                            if name in invalid
                            else "informational"
                            if name in informational
                            else "caution",
                            "pixels": int(((finite_flags & mask) != 0).sum()),
                        }
                    )
        wave = None
        if "WCS-WAVE" in hdus:
            try:
                row = hdus["WCS-WAVE"].data[0]
                x, y = np.ravel(row["X"]), np.ravel(row["Y"])
                values = np.asarray(row["VALUES"])
                px, py = native_wcs.world_to_pixel_values(s["ra"], s["dec"])
                # FITS lookup coordinates are 1-based; array indices are 0-based.
                if values.shape == (len(y), len(x), 2):
                    # Alternate WCS maps cutout pixels back to raw-detector lookup coordinates.
                    lx = (px + 1 - hdu.header.get("CRPIX1W", 1)) * hdu.header.get("CDELT1W", 1) + hdu.header.get(
                        "CRVAL1W", 1
                    )
                    ly = (py + 1 - hdu.header.get("CRPIX2W", 1)) * hdu.header.get("CDELT2W", 1) + hdu.header.get(
                        "CRVAL2W", 1
                    )
                    wave = RegularGridInterpolator((y, x), values, bounds_error=False, fill_value=np.nan)([[ly, lx]])[
                        0
                    ].tolist()
                    if not np.all(np.isfinite(wave)):
                        wave = None
            except (ValueError, KeyError, IndexError):
                pass
        ph = hdus[0].header
        from science.geometry import footprint as sky_footprint

        ys_valid, xs_valid = np.nonzero(valid)
        bounds = (
            (
                float(xs_valid.min()) - 0.5,
                float(ys_valid.min()) - 0.5,
                float(xs_valid.max()) + 0.5,
                float(ys_valid.max()) + 0.5,
            )
            if len(xs_valid)
            else None
        )
        return (
            arr,
            flags,
            {
                "units": hdu.header.get("BUNIT"),
                "archive_processing_version": ph.get("VERSION"),
                "wavelength_units": hdu.header.get("CUNIT1W"),
                "date": hdu.header.get("DATE-OBS", ph.get("DATE-OBS")),
                "timescale": hdu.header.get("TIMESYS", ph.get("TIMESYS")),
                "wavelength": wave,
                "wavelength_reason": None if wave else "Lookup layout not validated; no wavelength inferred",
                "coverage_fraction": float(valid.mean()),
                "header": target.to_header().tostring(),
                "native_shape": list(native.shape),
                "returned_footprint": sky_footprint(native_wcs, native.shape),
                "valid_data": {
                    "fraction": float(valid.mean()),
                    "policy": "Finite reprojected samples with nonzero archive footprint; quality flags remain separate",
                    "bounding_footprint": sky_footprint(target, shape, bounds) if bounds else None,
                    "bounding_note": "Bounding footprint may contain uncovered holes; fraction is measured from the actual valid-pixel mask",
                },
                "flag_values": [int(v) for v in np.unique(flags[np.isfinite(flags)])[:64]] if flags is not None else [],
                "decoded_flags": decoded_flags,
                "alignment": "WCS reprojection; residual not assessed",
                "mask_policy": "NaN and no-coverage excluded. Raw flags retained; release-specific invalid-bit decoding not yet validated.",
                "variance": "Native VARIANCE retained in original FITS; display interpolation has no propagated quantitative variance.",
            },
        )


def preview(array, low, high):
    valid = np.isfinite(array)
    scaled = np.arcsinh(
        np.clip((np.nan_to_num(array, nan=low) - low) / max(high - low, 1e-12), 0, 1) * 10
    ) / np.arcsinh(10)
    gray = (scaled * 255).astype("uint8")
    rgba = np.dstack([gray, gray, gray, valid.astype("uint8") * 255])
    image = Image.fromarray(np.flipud(rgba))
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def atomic_write(path, data):
    path.parent.mkdir(exist_ok=True, parents=True)
    tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
    return hashlib.sha256(data).hexdigest()


def weighted_stack(arrays, variances):
    a, v = np.asarray(arrays, float), np.asarray(variances, float)
    if a.shape != v.shape or a.ndim != 3:
        raise ValueError("Matching 3D arrays and variances required")
    ok = np.isfinite(a) & np.isfinite(v) & (v > 0)
    weights = np.divide(1, v, out=np.zeros_like(v), where=ok)
    den = weights.sum(axis=0)
    out = np.divide((np.where(ok, a, 0) * weights).sum(axis=0), den, out=np.full(a.shape[1:], np.nan), where=den > 0)
    variance = np.divide(1, den, out=np.full_like(den, np.nan), where=den > 0)
    return out, variance, ok.sum(axis=0)
