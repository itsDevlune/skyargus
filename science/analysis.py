"""Scientific extraction of spectra, difference images, and epoch stacks from SPHEREx observations.

Adapted from the official Caltech/IPAC SPHEREx tutorials:
- SPHEREx Spectral Image Cutouts (tutorials/spherex/spherex_cutouts.md)
- SPHEREx Source Discovery Tool (tutorials/spherex/spherex_source_discovery/spherex_source_discovery_tool_demo.md)
  and its aperture photometry module (aperture_photometry.py by Zafar Rustamkulov)
- Understanding and Analyzing SPHEREx Mosaic Cubes (tutorials/spherex/spherex_mosaic.md)
"""

from pathlib import Path

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
from photutils.aperture import CircularAnnulus, CircularAperture, aperture_photometry
from reproject import reproject_interp

from science.geometry import bandpass_comparison
from science.imaging import grid, preview, weighted_stack

ARCSEC2_TO_SR = (np.pi / (180.0 * 3600.0)) ** 2  # sr / arcsec^2
_AB_DMAG_FACTOR = 2.5 / np.log(10)  # 1.0857362047581296


def validate_frame_index(index, frame_count, name="frame index"):
    if isinstance(index, (bool, np.bool_)) or not isinstance(index, (int, np.integer)):
        raise ValueError(f"{name} must be an integer")
    index = int(index)
    if not 0 <= index < frame_count:
        raise ValueError(f"{name} must be between 0 and {frame_count - 1}")
    return index


def validate_frame_indices(indices, frame_count, name="frames"):
    if not isinstance(indices, (list, tuple)) or not indices:
        raise ValueError(f"{name} must be a non-empty list of frame indices")
    validated = [validate_frame_index(index, frame_count, f"{name} index") for index in indices]
    if len(set(validated)) != len(validated):
        raise ValueError(f"{name} must not contain duplicate frame indices")
    return validated


def extract_source_spectrum(sequence_manifest, ra, dec, data_dir, aperture_radius_pix=3.0):
    """Extract flux vs wavelength spectrum across dated exposures at a sky coordinate.

    Uses photutils circular aperture with local background annulus and variance propagation.
    Converts MJy/sr to mJy using the local pixel solid angle.
    Flags bad pixels using official SPHEREx MSKN bitmasks.
    """
    coord = SkyCoord(ra=float(ra) * u.deg, dec=float(dec) * u.deg, frame="icrs")
    frames = sequence_manifest.get("frames", [])
    measurements = []

    bad_flag_names = {
        "TRANSIENT", "OVERFLOW", "SUR_ERROR", "NONFUNC", "DICHROIC",
        "MISSING_DATA", "HOT", "COLD", "NONLINEAR", "CROSSTALK",
        "GHOST", "GHOST_FPA", "GHOST_EXT", "STREAK", "PERSIST",
        "BLOOM", "SNOWBALL", "HALO", "SATELLITE_HALO"
    }

    data_path = Path(data_dir)

    for i, frame in enumerate(frames):
        orig = frame.get("original")
        if not orig or not orig.get("id"):
            raise ValueError(f"Frame {i} has no original FITS artifact reference")
        from apps.core.models import Artifact

        try:
            art = Artifact.objects.get(id=orig["id"])
        except Artifact.DoesNotExist as exc:
            raise ValueError(f"Original FITS artifact for frame {i} is missing") from exc
        fits_path = data_path / art.filename
        if not fits_path.is_file():
            raise FileNotFoundError(f"Original FITS file for frame {i} is missing")

        with fits.open(fits_path, memmap=False) as hdus:
            if "IMAGE" not in hdus:
                raise ValueError(f"Original FITS file for frame {i} has no IMAGE HDU")
            img_hdu = hdus["IMAGE"]
            img_data = img_hdu.data
            var_data = hdus["VARIANCE"].data if "VARIANCE" in hdus else None
            flags_data = hdus["FLAGS"].data if "FLAGS" in hdus else None
            flags_hdr = hdus["FLAGS"].header if "FLAGS" in hdus else {}

            spatial_wcs = WCS(img_hdu.header).celestial
            # Compute position in this cutout
            x_pix, y_pix = spatial_wcs.world_to_pixel(coord)
            ny, nx = img_data.shape

            # Check if source is inside image bounds (with aperture margin)
            if not (aperture_radius_pix <= x_pix < nx - aperture_radius_pix and
                    aperture_radius_pix <= y_pix < ny - aperture_radius_pix):
                continue

            # Spectral WCS: tutorial method: key="W", sip=None
            # Alternate W maps detector coordinates to wavelength/bandwidth.
            # Primary celestial SIP coefficients do not belong to this mapping.
            # Remove them from a COPY before construction (not from archive data
            # or the spatial WCS), avoiding Astropy applying them implicitly.
            spectral_header = img_hdu.header.copy()
            import re
            for keyword in list(spectral_header):
                if re.fullmatch(r"(A|B|AP|BP)_(ORDER|\d+_\d+)", keyword):
                    del spectral_header[keyword]
            spectral_wcs = WCS(spectral_header, fobj=hdus, key="W")
            spectral_wcs.sip = None
            try:
                wl_val, bw_val = spectral_wcs.pixel_to_world(x_pix, y_pix)
                wavelength_um = float(wl_val.to(u.micrometer).value)
                bandwidth_um = float(bw_val.to(u.micrometer).value)
            except Exception:
                # Fallback to field center wavelength if lookup fails
                wl_info = frame.get("wavelength")
                if wl_info:
                    wavelength_um, bandwidth_um = float(wl_info[0]), float(wl_info[1])
                else:
                    continue

            # Pixel solid angle from WCS
            scales = proj_plane_pixel_scales(spatial_wcs) * 3600  # arcsec / pix
            sa_arcsec2 = float(scales[0] * scales[1])
            # Scale factor: [mJy/pix] per [MJy/sr]
            scale_to_mjy = sa_arcsec2 * ARCSEC2_TO_SR * 1e9

            # Aperture photometry with background annulus
            pos = (x_pix, y_pix)
            ap = CircularAperture(pos, r=aperture_radius_pix)
            ann = CircularAnnulus(pos, r_in=max(aperture_radius_pix + 2.0, 5.0), r_out=max(aperture_radius_pix + 5.0, 8.0))

            phot = aperture_photometry(img_data, ap)
            ann_mask = ann.to_mask(method="center")
            cut_vals = ann_mask.multiply(img_data)
            ann_vals = cut_vals[ann_mask.data > 0]
            ann_finite = ann_vals[np.isfinite(ann_vals)]

            if len(ann_finite) > 5:
                _, bkg_med, _ = sigma_clipped_stats(ann_finite, sigma=3.0, maxiters=5)
            else:
                bkg_med = 0.0

            aperture_sum_raw = float(phot["aperture_sum"][0])
            bkg_sub_raw = aperture_sum_raw - float(bkg_med) * ap.area
            flux_mjy = bkg_sub_raw * scale_to_mjy

            # Variance propagation
            if var_data is not None:
                var_phot = aperture_photometry(var_data, ap)
                var_sum = float(var_phot["aperture_sum"][0])
                flux_err_mjy = np.sqrt(max(var_sum, 0.0)) * scale_to_mjy
                var_mjy2 = var_sum * (scale_to_mjy ** 2)
            else:
                flux_err_mjy = np.nan
                var_mjy2 = np.nan

            # AB Magnitude
            if flux_mjy > 0:
                abmag = float(-2.5 * np.log10(flux_mjy * 1e-3 / 3631.0))
                abmag_err = float(_AB_DMAG_FACTOR * (flux_err_mjy / flux_mjy)) if np.isfinite(flux_err_mjy) else np.nan
            else:
                abmag = np.nan
                abmag_err = np.nan

            # Count bad flag pixels
            bad_pixel_count = 0
            flag_details = {}
            if flags_data is not None and flags_hdr:
                for k, v in flags_hdr.items():
                    if k.startswith("MSKN"):
                        name = str(v).strip()
                        mask_val = int(flags_hdr.get("MSKM" + k[4:], 0))
                        has_flag = ((flags_data & mask_val) != 0).astype(int)
                        count_in_ap = float(aperture_photometry(has_flag, ap, method="center")["aperture_sum"][0])
                        if count_in_ap > 0:
                            flag_details[name] = count_in_ap
                            if name in bad_flag_names:
                                bad_pixel_count += count_in_ap

            measurements.append({
                "frame_index": i,
                "observation_id": frame.get("id"),
                "date": frame.get("date"),
                "detector": frame.get("detector"),
                "wavelength_um": round(wavelength_um, 4),
                "bandwidth_um": round(bandwidth_um, 4),
                "flux_mjy": round(flux_mjy, 4),
                "flux_err_mjy": round(flux_err_mjy, 4) if np.isfinite(flux_err_mjy) else None,
                "variance_mjy2": round(var_mjy2, 6) if np.isfinite(var_mjy2) else None,
                "abmag": round(abmag, 2) if np.isfinite(abmag) else None,
                "abmag_err": round(abmag_err, 2) if np.isfinite(abmag_err) else None,
                "bad_pixel_count": int(bad_pixel_count),
                "flags": flag_details,
                "pixel_x": round(float(x_pix), 2),
                "pixel_y": round(float(y_pix), 2),
            })

    # Sort measurements chronologically and by wavelength
    measurements.sort(key=lambda m: (m["date"] or "", m["wavelength_um"]))

    return {
        "target_coordinates": {"ra": float(ra), "dec": float(dec)},
        "aperture_radius_pixels": aperture_radius_pix,
        "measurement_count": len(measurements),
        "measurements": measurements,
        "method": "Aperture photometry on un-reprojected native cutouts with local background subtraction and WCS pixel scale conversion",
        "units": {"flux": "mJy", "variance": "mJy^2", "wavelength": "um", "bandwidth": "um"},
        "warning": "Quick-look aperture extraction. Accurate quantitative photometry requires full ePSF fitting per SPHEREx Explanatory Supplement."
    }


def compute_frame_difference(sequence_manifest, frame_a_idx, frame_b_idx, data_dir):
    """Compute difference image (Frame B - Frame A) on the common target grid.

    Requires wavelength compatibility check. Propagates variance: Var(B - A) = Var(B) + Var(A).
    Produces zero-centered preview stretch and scientific residual array.
    """
    frames = sequence_manifest.get("frames", [])
    frame_a_idx = validate_frame_index(frame_a_idx, len(frames), "frame_a")
    frame_b_idx = validate_frame_index(frame_b_idx, len(frames), "frame_b")
    if frame_a_idx == frame_b_idx:
        raise ValueError("frame_a and frame_b must refer to different observations")

    fa, fb = frames[frame_a_idx], frames[frame_b_idx]
    target_wcs, shape = grid(sequence_manifest["selection"])
    data_path = Path(data_dir)

    def load_reprojected(frame):
        from apps.core.models import Artifact
        art = Artifact.objects.get(id=frame["original"]["id"])
        hdus = fits.open(data_path / art.filename)
        nw = WCS(hdus["IMAGE"].header).celestial
        img_rep, fp = reproject_interp((hdus["IMAGE"].data.astype(float), nw), target_wcs, shape_out=shape)
        var_rep, _ = reproject_interp((hdus["VARIANCE"].data.astype(float), nw), target_wcs, shape_out=shape)
        flags_rep, _ = reproject_interp((hdus["FLAGS"].data.astype(float), nw), target_wcs, shape_out=shape, order="nearest-neighbor")
        # Quality mask: SUR_ERROR, MISSING_DATA, NONFUNC, HOT, COLD
        bad_bits = 4 | 64 | 512 | 1024 | 2048
        finite_flags = np.nan_to_num(flags_rep, nan=0.0).astype(int)
        flag_bad = (finite_flags & bad_bits) != 0
        ok = (fp > 0) & np.isfinite(img_rep) & np.isfinite(var_rep) & (var_rep > 0) & (~flag_bad)
        img_rep[~ok] = np.nan
        var_rep[~ok] = np.nan
        return img_rep, var_rep

    img_a, var_a = load_reprojected(fa)
    img_b, var_b = load_reprojected(fb)

    # Difference: B - A
    diff_arr = img_b - img_a
    diff_var = var_b + var_a
    valid_diff = np.isfinite(diff_arr) & np.isfinite(diff_var)

    wl_a = fa.get("wavelength")
    wl_b = fb.get("wavelength")
    bandpass = bandpass_comparison(fa, fb)
    nominal_bandpass_overlap = bandpass["status"] == "overlapping_display_bandpasses"
    if nominal_bandpass_overlap:
        warning = (
            "Nominal field-center display bandpasses overlap. Calibrated spectral response, measured alignment, "
            "background matching, and PSF matching are not assessed."
        )
    elif bandpass["status"] == "disjoint_display_bandpasses":
        warning = (
            "Nominal field-center display bandpasses are disjoint; residuals may reflect spectral slope rather than "
            "temporal change. Calibrated response, measured alignment, background matching, and PSF matching are "
            "not assessed."
        )
    else:
        warning = (
            "Nominal display bandpass overlap is not assessed. Calibrated spectral response, measured alignment, "
            "background matching, and PSF matching are not assessed."
        )

    # Zero-centered stretch for preview
    finite_diff = diff_arr[valid_diff]
    if len(finite_diff) > 0:
        lim = float(np.nanpercentile(np.abs(finite_diff), 98))
        lim = max(lim, 1e-6)
    else:
        lim = 1.0
    lo, hi = -lim, lim

    preview_png = preview(diff_arr, lo, hi)

    return {
        "frame_a": {
            "index": frame_a_idx,
            "id": fa.get("id"),
            "date": fa.get("date"),
            "wavelength": wl_a
        },
        "frame_b": {
            "index": frame_b_idx,
            "id": fb.get("id"),
            "date": fb.get("date"),
            "wavelength": wl_b
        },
        "nominal_bandpass_overlap": nominal_bandpass_overlap if bandpass["status"] != "not_assessed" else None,
        "bandpass_comparison": bandpass,
        "response_comparability": "not_assessed",
        "wavelength_separation_um": round(bandpass["center_difference_um"], 4)
        if bandpass.get("center_difference_um") is not None
        else None,
        "valid_pixel_count": int(valid_diff.sum()),
        "total_pixels": int(diff_arr.size),
        "residual_min": float(np.nanmin(diff_arr)) if np.any(valid_diff) else None,
        "residual_max": float(np.nanmax(diff_arr)) if np.any(valid_diff) else None,
        "residual_median": float(np.nanmedian(diff_arr)) if np.any(valid_diff) else None,
        "preview_png": preview_png,
        "display_limits": {"low": lo, "high": hi},
        "warning": warning,
    }


def compute_epoch_stack(sequence_manifest, frame_indices, data_dir):
    """Compute quality-masked inverse-variance weighted stack across selected frames.

    Aligns spatial grids, applies documented quality bitmasks, weights by 1/Variance,
    and propagates combined uncertainty.
    """
    frames = sequence_manifest.get("frames", [])
    frame_indices = validate_frame_indices(frame_indices, len(frames), "frames")
    selected_frames = [frames[i] for i in frame_indices]
    bandpass_comparisons = [
        bandpass_comparison(selected_frames[0], frame) for frame in selected_frames[1:]
    ]
    if any(item["status"] == "disjoint_display_bandpasses" for item in bandpass_comparisons):
        raise ValueError("Cannot stack observations with disjoint nominal display bandpasses")
    if len(selected_frames) > 1 and any(
        item["status"] != "overlapping_display_bandpasses" for item in bandpass_comparisons
    ):
        raise ValueError("Cannot assess nominal display bandpass overlap for every selected observation")

    target_wcs, shape = grid(sequence_manifest["selection"])
    data_path = Path(data_dir)

    arrs, vars_ = [], []
    contributors = []

    for idx, f in zip(frame_indices, selected_frames, strict=True):
        from apps.core.models import Artifact
        art = Artifact.objects.get(id=f["original"]["id"])
        hdus = fits.open(data_path / art.filename)
        nw = WCS(hdus["IMAGE"].header).celestial
        img_rep, fp = reproject_interp((hdus["IMAGE"].data.astype(float), nw), target_wcs, shape_out=shape)
        var_rep, _ = reproject_interp((hdus["VARIANCE"].data.astype(float), nw), target_wcs, shape_out=shape)
        flags_rep, _ = reproject_interp((hdus["FLAGS"].data.astype(float), nw), target_wcs, shape_out=shape, order="nearest-neighbor")

        bad_bits = 4 | 64 | 512 | 1024 | 2048 | 32768
        finite_flags = np.nan_to_num(flags_rep, nan=0.0).astype(int)
        flag_bad = (finite_flags & bad_bits) != 0
        ok = (fp > 0) & np.isfinite(img_rep) & np.isfinite(var_rep) & (var_rep > 0) & (~flag_bad)

        clean_img = np.where(ok, img_rep, np.nan)
        clean_var = np.where(ok, var_rep, np.nan)

        arrs.append(clean_img)
        vars_.append(clean_var)
        contributors.append({
            "index": idx,
            "id": f.get("id"),
            "date": f.get("date"),
            "wavelength": f.get("wavelength"),
            "valid_fraction": float(ok.mean())
        })

    stacked_img, stacked_var, hits = weighted_stack(arrs, vars_)
    valid = np.isfinite(stacked_img)

    finite_vals = stacked_img[valid]
    if len(finite_vals) > 0:
        lo = float(np.nanpercentile(finite_vals, 1))
        hi = float(np.nanpercentile(finite_vals, 99))
    else:
        lo, hi = 0.0, 1.0

    preview_png = preview(stacked_img, lo, hi)

    return {
        "contributors": contributors,
        "contributor_count": len(contributors),
        "hits_min": int(np.min(hits)),
        "hits_max": int(np.max(hits)),
        "valid_pixel_count": int(valid.sum()),
        "total_pixels": int(stacked_img.size),
        "flux_min": float(np.nanmin(stacked_img)) if np.any(valid) else None,
        "flux_max": float(np.nanmax(stacked_img)) if np.any(valid) else None,
        "preview_png": preview_png,
        "display_limits": {"low": lo, "high": hi},
        "method": "Inverse-variance weighted stack on reprojected grid with MSKN bad-pixel exclusion",
        "bandpass_comparison": {
            "status": "overlapping_display_bandpasses" if bandpass_comparisons else "not_assessed",
            "reference_observation_id": selected_frames[0].get("id"),
            "comparisons": bandpass_comparisons,
            "reason": "Nominal field-center WCS-WAVE lookup only; calibrated response comparability is not established.",
        },
        "response_comparability": "not_assessed",
        "warning": (
            "Nominal display bandpasses overlap. Calibrated spectral response, measured alignment, background "
            "matching, and PSF matching are not assessed."
            if bandpass_comparisons
            else "Single-observation stack; response comparability is not assessed."
        ),
        "units": "MJy/sr",
        "stacked_array": stacked_img,
        "stacked_var": stacked_var
    }


def compute_spectral_composite(sequence_manifest, red_idx, green_idx, blue_idx, data_dir):
    """Construct an RGB false-colour composite mapping three selected frames to RGB channels.

    Discloses wavelength mapping, date ranges, and per-channel stretch.
    """
    frames = sequence_manifest.get("frames", [])
    red_idx, green_idx, blue_idx = (
        validate_frame_index(index, len(frames), name)
        for index, name in ((red_idx, "red"), (green_idx, "green"), (blue_idx, "blue"))
    )
    if len({red_idx, green_idx, blue_idx}) != 3:
        raise ValueError("RGB channels must refer to three different observations")

    fr, fg, fb = frames[red_idx], frames[green_idx], frames[blue_idx]
    target_wcs, shape = grid(sequence_manifest["selection"])
    data_path = Path(data_dir)

    def load_channel(f):
        from apps.core.models import Artifact
        art = Artifact.objects.get(id=f["aligned"]["id"])
        data = fits.open(data_path / art.filename)[0].data.astype(float)
        v = np.nan_to_num(data, nan=0.0)
        pos = v[v > 0]
        lo = float(np.nanpercentile(pos, 2)) if len(pos) > 10 else 0.0
        hi = float(np.nanpercentile(pos, 98)) if len(pos) > 10 else 1.0
        scaled = np.arcsinh(np.clip((v - lo) / max(hi - lo, 1e-12), 0, 1) * 10) / np.arcsinh(10)
        return (scaled * 255).astype("uint8"), lo, hi

    r_bytes, r_lo, r_hi = load_channel(fr)
    g_bytes, g_lo, g_hi = load_channel(fg)
    b_bytes, b_lo, b_hi = load_channel(fb)

    import io

    from PIL import Image
    rgb_arr = np.dstack([r_bytes, g_bytes, b_bytes])
    img = Image.fromarray(np.flipud(rgb_arr))
    out = io.BytesIO()
    img.save(out, format="PNG")

    return {
        "mapping": {
            "red": {
                "index": red_idx,
                "id": fr.get("id"),
                "date": fr.get("date"),
                "wavelength": fr.get("wavelength"),
                "stretch": {"low": r_lo, "high": r_hi}
            },
            "green": {
                "index": green_idx,
                "id": fg.get("id"),
                "date": fg.get("date"),
                "wavelength": fg.get("wavelength"),
                "stretch": {"low": g_lo, "high": g_hi}
            },
            "blue": {
                "index": blue_idx,
                "id": fb.get("id"),
                "date": fb.get("date"),
                "wavelength": fb.get("wavelength"),
                "stretch": {"low": b_lo, "high": b_hi}
            }
        },
        "preview_png": out.getvalue(),
        "dimensions": [shape[1], shape[0]],
        "method": "Per-channel arcsinh normalized false-colour RGB rendering of reprojected surface brightnesses",
        "response_comparability": "not_assessed",
        "warning": "False-colour visualization only; per-channel display stretches do not provide calibrated colour or photometry.",
    }
