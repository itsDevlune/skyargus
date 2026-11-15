import hashlib
import json
import logging
import time
import uuid

import numpy as np
from astropy.time import Time
from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from science.imaging import atomic_write, grid, preview, read_frame

from .errors import archive_error
from .models import Artifact, Dispatch, Job, Sequence
from .network import get
from .providers import discovery, gaia, wise

log = logging.getLogger(__name__)


def cache_key(selection):
    return hashlib.sha256(json.dumps(selection, sort_keys=True).encode()).hexdigest()


def store(sequence, data, suffix, media):
    artifact = Artifact(
        id=uuid.uuid4(), sequence=sequence, filename=uuid.uuid4().hex + suffix, media_type=media, size=len(data)
    )
    artifact.sha256 = atomic_write(settings.DATA_ROOT / artifact.filename, data)
    artifact.save()
    return {
        "id": str(artifact.id),
        "url": f"/api/v1/artifacts/{artifact.id}",
        "sha256": artifact.sha256,
        "bytes": len(data),
        "type": media,
    }


def persist_attempt(job_id, attempt, **updates):
    now = timezone.now()
    updates["updated"] = now
    if Job.objects.filter(pk=job_id, state="running", attempts=attempt).update(**updates):
        return True
    Job.objects.filter(pk=job_id, state="cancel_requested", attempts=attempt).update(
        state="cancelled",
        stage="Cancelled; stored shared evidence preserved",
        updated=now,
    )
    return False


def update(job, stage, attempt):
    return persist_attempt(job.id, attempt, stage=stage)


@shared_task(name="argus.run", acks_late=True)
def run_job(job_id):
    with transaction.atomic():
        claimed = Job.objects.filter(pk=job_id, state="queued").update(
            state="running",
            attempts=F("attempts") + 1,
            updated=timezone.now(),
        )
        if not claimed:
            return
        job = Job.objects.get(pk=job_id)
        attempt = job.attempts
    started = time.monotonic()
    try:
        if job.kind == 'cube':
            import io

            from astropy import units as u
            from astropy_healpix import HEALPix

            from science.cubes import cube_info

            hp = HEALPix(nside=32, order='nested', frame='icrs')
            tile = int(hp.lonlat_to_healpix(job.selection['ra'] * u.deg, job.selection['dec'] * u.deg))
            key = cache_key({'cube': 'DR1-hips_20261026-complete-v2', 'tile': tile})
            sequence = Sequence.objects.filter(cache_key=key).first()
            if sequence and sequence.manifest.get('cube'):
                info = sequence.manifest['cube']
            else:
                url = f'https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/hips5_cube/hips_20261026/Norder5/Dir{tile // 10000 * 10000}/Npix{tile}_cube.fits'
                update(job, 'Downloading genuine 102-channel DR1 cube (up to 384 MiB)', attempt)
                from .cube_download import download_cube
                def cube_progress(received, total):
                    if not update(job, f'Cube transfer: {received // 1048576}/{total // 1048576} MiB verified; retry resumes saved chunks', attempt):
                        raise ValueError('Cube request cancelled; verified transfer chunks retained')

                raw = download_cube(url, cache_dir=settings.DATA_ROOT / 'cube-transfers', progress=cube_progress)
                if not update(job, 'Validating actual 102-plane cube and channel metadata', attempt):
                    return
                info = cube_info(io.BytesIO(raw))
                sequence, _ = Sequence.objects.get_or_create(cache_key=key, defaults={'manifest': {}})
                info.update({'artifact': store(sequence, raw, '.fits', 'application/fits'), 'tile': tile, 'archive_url': url})
                sequence.manifest = {'cube': info}
                sequence.save(update_fields=['manifest'])
            persist_attempt(job.id, attempt, state='completed', stage='102-channel cube ready', error={}, result={'cube_id': str(sequence.id), **info})
            return
        if job.kind == "motion":
            from science.motion import fit_motion

            result = fit_motion(job.selection["points"], job.selection["position_error_arcsec"])
            persist_attempt(
                job.id,
                attempt,
                result=result,
                state="completed",
                stage="Manual apparent-motion fit complete",
            )
            return
        if job.kind == "spectrum":
            from science.analysis import extract_source_spectrum

            seq = Sequence.objects.get(pk=job.selection["sequence"])
            ra = job.selection["ra"]
            dec = job.selection["dec"]
            ap_rad = float(job.selection.get("aperture_radius_pix", 3.0))
            result = extract_source_spectrum(seq.manifest, ra, dec, settings.DATA_ROOT, ap_rad)
            persist_attempt(
                job.id,
                attempt,
                result=result,
                state="completed",
                stage="Source spectrum extracted",
            )
            return
        if job.kind == "difference":
            from science.analysis import compute_frame_difference

            seq = Sequence.objects.get(pk=job.selection["sequence"])
            fa = job.selection["frame_a"]
            fb = job.selection["frame_b"]
            diff_res = compute_frame_difference(seq.manifest, fa, fb, settings.DATA_ROOT)
            if not update(job, "Storing difference preview", attempt):
                return
            # Store PNG preview artifact
            preview_bytes = diff_res.pop("preview_png")
            artifact_info = store(seq, preview_bytes, ".png", "image/png")
            diff_res["preview"] = artifact_info
            persist_attempt(
                job.id,
                attempt,
                result=diff_res,
                state="completed",
                stage="Image difference complete",
            )
            return
        if job.kind == "stack":
            from science.analysis import compute_epoch_stack

            seq = Sequence.objects.get(pk=job.selection["sequence"])
            frame_indices = job.selection["frames"]
            stack_res = compute_epoch_stack(seq.manifest, frame_indices, settings.DATA_ROOT)
            if not update(job, "Storing stack preview and FITS", attempt):
                return
            preview_bytes = stack_res.pop("preview_png")
            stack_arr = stack_res.pop("stacked_array")
            stack_var = stack_res.pop("stacked_var")
            artifact_info = store(seq, preview_bytes, ".png", "image/png")
            stack_res["preview"] = artifact_info
            # Store stacked FITS artifact
            import io

            from astropy.io import fits

            fits_buf = io.BytesIO()
            target_wcs, _ = grid(seq.manifest["selection"])
            fits_hdr = target_wcs.to_header()
            fits_hdr["BUNIT"] = "MJy/sr"
            hdul = fits.HDUList(
                [
                    fits.PrimaryHDU(data=stack_arr.astype(np.float32), header=fits_hdr),
                    fits.ImageHDU(data=stack_var.astype(np.float32), name="VARIANCE"),
                ]
            )
            hdul.writeto(fits_buf)
            fits_artifact = store(seq, fits_buf.getvalue(), ".fits", "application/fits")
            stack_res["fits"] = fits_artifact
            persist_attempt(
                job.id,
                attempt,
                result=stack_res,
                state="completed",
                stage="Epoch stack complete",
            )
            return
        if job.kind == "composite":
            from science.analysis import compute_spectral_composite

            seq = Sequence.objects.get(pk=job.selection["sequence"])
            r_idx = job.selection["red"]
            g_idx = job.selection["green"]
            b_idx = job.selection["blue"]
            comp_res = compute_spectral_composite(seq.manifest, r_idx, g_idx, b_idx, settings.DATA_ROOT)
            if not update(job, "Storing composite preview", attempt):
                return
            preview_bytes = comp_res.pop("preview_png")
            artifact_info = store(seq, preview_bytes, ".png", "image/png")
            comp_res["preview"] = artifact_info
            persist_attempt(
                job.id,
                attempt,
                result=comp_res,
                state="completed",
                stage="Spectral composite complete",
            )
            return
        if job.kind in ("gaia", "wise"):
            result = (wise if job.kind == "wise" else gaia)(job.selection)
            persist_attempt(
                job.id,
                attempt,
                result=result,
                state="completed",
                stage="AllWISE query complete" if job.kind == "wise" else "Gaia DR3 query complete",
            )
            return
        if job.kind != 'sequence':
            raise ValueError(f'Unsupported processing job kind: {job.kind}')
        s = job.selection
        key = cache_key(s)
        cached = Sequence.objects.filter(cache_key=key).first()
        if cached:
            persist_attempt(
                job.id,
                attempt,
                result={"sequence": str(cached.id)},
                state="completed",
                stage="Loaded persistent cache",
            )
            return
        if not update(job, "Discovering dated archive observations", attempt):
            return
        try:
            rows, metadata = discovery(s)
        except Exception as exc:
            from .cached_observations import discover_cached

            recovered = discover_cached(s, exc)
            if recovered is None:
                raise
            rows, metadata = recovered
            # Keep incomplete cache recovery separate from a successful live search.
            key = cache_key({**s, "cached_native_inputs": [r["cached_original_sha256"] for r in rows]})
        from .cached_observations import cached_candidates, read_cached_original

        candidates = cached_candidates(s) if metadata.get("mode") != "cached-native-recovery-v1" else (rows, {})
        saved_by_url = {r["url"]: r for r in candidates[0]} if candidates else {}
        arrays, originals, frames, excluded = [], [], [], []
        downloaded_bytes = 0
        for i, row in enumerate(rows):
            if time.monotonic() - started > 210:
                excluded.extend(
                    {"id": remaining["id"], "reason": "Per-job processing time budget reached"}
                    for remaining in rows[i:]
                )
                break
            if not update(job, f"Downloading and aligning {i + 1} of {len(rows)}", attempt):
                return
            try:
                # Oversized square ensures rotated detector cutout contains the requested rectangular sky grid.
                size = min(30, (s["width"] ** 2 + s["height"] ** 2) ** 0.5 * 1.15)
                params = (
                    {"center": f"{s['ra']},{s['dec']}deg", "size": f"{size}arcmin", "gzip": "false"}
                    if s["source"] == "spherex"
                    else {}
                )
                download_key = hashlib.sha256(json.dumps([row["url"], params], sort_keys=True).encode()).hexdigest()
                download_path = settings.DATA_ROOT / "downloads" / (download_key + ".fits")
                saved = saved_by_url.get(row["url"])
                if saved and saved["cached_covers_output"]:
                    row.update({k: v for k, v in saved.items() if k.startswith("cached_")})
                if row.get("cached_original_id"):
                    raw = read_cached_original(row)
                    row["cutout_reused"] = True
                elif download_path.exists():
                    raw = download_path.read_bytes()
                else:
                    try:
                        raw = get(row["url"], params)
                        downloaded_bytes += len(raw)
                        atomic_write(download_path, raw)
                    except Exception as exc:
                        if not saved or not archive_error(exc)["retryable"]:
                            raise
                        raw = read_cached_original(saved)
                        row.update({k: v for k, v in saved.items() if k.startswith("cached_")})
                        row["cutout_reused"] = True
                        row["cutout_archive_error"] = archive_error(exc)
                        metadata["cached_cutout_recovery"] = True
                        metadata["warning"] = (
                            "Some archive cutouts failed; retained original cached cutouts were reprojected. Native edges can reduce valid coverage."
                        )
                if s["source"] == "neossat":
                    from .neossat import read_native

                    array, flags, meta = read_native(raw)
                    if arrays and array.shape != arrays[0].shape:
                        raise ValueError("Different native detector shape; not a comparable native sequence")
                else:
                    array, flags, meta = read_frame(raw, s)
                if not np.isfinite(array).any():
                    raise ValueError("No finite pixels in requested sky grid")
                arrays.append(array)
                originals.append(raw)
                row.update(meta)
                if not row["date"] and row.get("mjd"):
                    row["date"] = Time(row["mjd"], format="mjd").isot
                row["cutout_parameters"] = (
                    params
                    if not row.get("cutout_reused")
                    else {"requested_output": s, "native_cutout": "Retained cached input; not refetched or expanded"}
                )
                row["flags_available"] = flags is not None
                frames.append(row)
            except Exception as exc:
                log.warning("Excluded observation %s: %s", row["id"], exc)
                error = archive_error(exc)
                excluded.append(
                    {
                        "id": row["id"],
                        "reason": error["message"],
                        "code": error["code"],
                        "retryable": error["retryable"],
                    }
                )
        if not update(job, "Rendering shared-stretch previews and writing provenance", attempt):
            return
        if arrays:
            values = np.concatenate([a[np.isfinite(a)] for a in arrays])
            low, high = map(float, np.percentile(values, [1, 99.5]))
        else:
            low, high = 0.0, 1.0
        w, shape = grid(s)
        native_mode = s["source"] == "neossat"
        if native_mode and arrays:
            shape = arrays[0].shape
        with transaction.atomic():
            sequence, created = Sequence.objects.get_or_create(cache_key=key, defaults={"manifest": {}})
            if created:
                for frame, arr, raw in zip(frames, arrays, originals):
                    frame["preview"] = store(sequence, preview(arr, low, high), ".png", "image/png")
                    frame["original"] = store(sequence, raw, ".fits", "application/fits")
                    import io

                    from astropy.io import fits

                    out = io.BytesIO()
                    header = fits.Header() if native_mode else w.to_header()
                    header["BUNIT"] = frame["units"] or "unknown"
                    header["HISTORY"] = (
                        "Argus display-grid interpolation. No propagated variance; not a photometric product."
                    )
                    fits.PrimaryHDU(arr.astype("float32"), header).writeto(out)
                    frame["aligned"] = store(sequence, out.getvalue(), ".fits", "application/fits")
                manifest = {
                    "schema_version": 1,
                    "id": str(sequence.id),
                    "data_mode": "real",
                    "selection": s,
                    "frames": frames,
                    "excluded": excluded,
                    "discovery": metadata,
                    "created": timezone.now().isoformat(),
                    "geometry": {
                        "mode": "native" if native_mode else "celestial",
                        "width": shape[1],
                        "height": shape[0],
                        "wcs": None if native_mode else w.to_header().tostring(),
                        "pixel_scale_arcsec": None if native_mode else 6.2,
                        "orientation": "Native detector; sky orientation not assessed"
                        if native_mode
                        else "North up; east left; TAN projection",
                        "crpix": None if native_mode else w.wcs.crpix.tolist(),
                        "crval": None if native_mode else w.wcs.crval.tolist(),
                        "cdelt": None if native_mode else w.wcs.cdelt.tolist(),
                    },
                    "display": {"low": low, "high": high, "stretch": "asinh(10x)", "shared": True},
                    "warnings": [
                        metadata.get("warning", "Real SPHEREx dated exposures"),
                        "WCS alignment residual not assessed.",
                        "Local spectral-response comparability not assessed; blinking does not establish variability.",
                        "Quantitative photometry requires calibration products and validated flag/PSF treatment.",
                    ],
                    "metrics": {
                        "seconds": round(time.monotonic() - started, 3),
                        "input_fits_bytes": sum(map(len, originals)),
                        "network_download_bytes": downloaded_bytes,
                    },
                }
                sequence.manifest = manifest
                sequence.save()
        state = (
            "partial"
            if excluded
            or not frames
            or metadata.get("mode") == "cached-native-recovery-v1"
            or metadata.get("cached_cutout_recovery")
            else "completed"
        )
        stage = (
            f"{len(frames)} usable observations; {len(excluded)} excluded"
            if rows
            else "No matching observations returned"
        )
        persist_attempt(
            job.id,
            attempt,
            result={"sequence": str(sequence.id)},
            state=state,
            stage=stage,
        )
    except Exception as exc:
        failure = archive_error(exc)
        if job.kind == 'cube' and failure['retryable'] and attempt < 4:
            queued = persist_attempt(
                job.id, attempt, state='queued',
                stage=f'Cube transfer paused; resuming verified chunks (attempt {attempt + 1}/4)',
                error={},
            )
            log.warning('Cube job %s transfer paused; verified chunks retained, attempt %s/4', job_id, attempt)
            if queued:
                publish(job.id)
            return
        if failure['retryable']:
            log.warning('Job %s: %s', job_id, failure['message'])
        else:
            log.exception("Job %s failed", job_id)
        if job.kind == 'cube' and failure['retryable']:
            failure = {**failure, 'message': 'Cube transfer paused after four bounded attempts. Verified chunks are retained; click Resume cube download to continue.'}
        persist_attempt(
            job.id,
            attempt,
            state="failed",
            stage="Archive or processing request failed",
            error=failure,
        )


def publish(job_id):
    import os

    if os.getenv("ARGUS_DISPATCH", "database") == "celery":
        try:
            run_job.apply_async(args=[str(job_id)], retry=False)
            Dispatch.objects.filter(job_id=job_id).update(published=timezone.now())
        except Exception:
            log.exception("Dispatch deferred; durable intent remains for reconciliation")
