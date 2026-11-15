"""Recover bounded, real native inputs when fresh archive discovery fails.

Never reuse an old display image at different coordinates or treat cached
observations as a complete archive search. New outputs use the current WCS grid.
"""

import hashlib

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS
from django.conf import settings

from science.coordinates import footprint_search_radius_deg
from science.imaging import grid

from .errors import archive_error
from .models import Artifact, Sequence


def discover_cached(selection, failure):
    if selection["source"] != "spherex" or not archive_error(failure)["retryable"]:
        return None
    recovered = cached_candidates(selection)
    if recovered is None:
        return None
    rows, metadata = recovered
    metadata.update(
        {
            "mode": "cached-native-recovery-v1",
            "archive_search_succeeded": False,
            "archive_error": archive_error(failure),
            "warning": "Archive search unavailable: using overlapping locally saved original FITS. "
            "Archive/time coverage is incomplete; native cutout edges can reduce valid coverage.",
        }
    )
    return rows, metadata


def cached_candidates(selection):
    if selection["source"] != "spherex":
        return None
    target, shape = grid(selection)
    # Pixel-edge corners bound this small TAN field. A conservative native bbox
    # test chooses candidates; reprojection later rejects any zero-valid overlap.
    x = np.array([-0.5, shape[1] - 0.5, shape[1] - 0.5, -0.5])
    y = np.array([-0.5, -0.5, shape[0] - 0.5, shape[0] - 0.5])
    ra, dec = target.pixel_to_world_values(x, y)
    requested_centre = SkyCoord(selection["ra"], selection["dec"], unit="deg")
    requested_radius = footprint_search_radius_deg(selection["width"], selection["height"])
    rows, seen, inspected = [], set(), set()
    sequences = Sequence.objects.filter(
        manifest__selection__source="spherex",
        manifest__selection__release=selection["release"],
        manifest__selection__detector=selection["detector"],
    ).order_by("-created")[:100]
    start = Time(selection["start"]).mjd if selection.get("start") else -np.inf
    end = Time(selection["end"]).mjd + 1 if selection.get("end") else np.inf
    for sequence in sequences:
        for frame in sequence.manifest.get("frames", []):
            if len(inspected) >= 400:
                break
            original = frame.get("original", {})
            identity = frame.get("id")
            if not identity or identity in seen or original.get("id") in inspected:
                continue
            inspected.add(original.get("id"))
            try:
                artifact = Artifact.objects.get(pk=original["id"], sequence=sequence)
                if artifact.size > 32 * 1024**2:
                    continue
                path = settings.DATA_ROOT / artifact.filename
                with fits.open(path, memmap=True) as hdus:
                    image = hdus["IMAGE"]
                    native = WCS(image.header, hdus).celestial
                    height, width = image.shape
                    centre = native.pixel_to_world((width - 1) / 2, (height - 1) / 2)
                    corners = native.pixel_to_world(
                        [-0.5, width - 0.5, width - 0.5, -0.5],
                        [-0.5, -0.5, height - 0.5, height - 0.5],
                    )
                    if centre.separation(requested_centre).deg > max(centre.separation(corners).deg) + requested_radius:
                        continue
                    px, py = native.world_to_pixel_values(ra, dec)
                    if (
                        not np.isfinite(px).all()
                        or not np.isfinite(py).all()
                        or max(px) < -0.5
                        or min(px) > width - 0.5
                        or max(py) < -0.5
                        or min(py) > height - 0.5
                    ):
                        continue
                    date = image.header.get("DATE-OBS", hdus[0].header.get("DATE-OBS"))
                    mjd = Time(date).mjd
                    if not start <= mjd < end:
                        continue
                rows.append(
                    {
                        "id": identity,
                        "url": frame["url"],
                        "mjd": float(mjd),
                        "end_mjd": frame.get("end_mjd"),
                        "source": "SPHEREx",
                        "release": selection["release"],
                        "detector": selection["detector"],
                        "cached_original_id": str(artifact.id),
                        "cached_original_sha256": artifact.sha256,
                        "cached_parent_sequence": str(sequence.id),
                        "cached_covers_output": bool(
                            np.all((px >= -0.5) & (px <= width - 0.5) & (py >= -0.5) & (py <= height - 0.5))
                        ),
                        "input_extent": "Previously downloaded native cutout, not necessarily the full archive image",
                    }
                )
                seen.add(identity)
            except (KeyError, ValueError, OSError, Artifact.DoesNotExist):
                continue
    if not rows:
        return None
    from .providers import select_epochs

    selected = select_epochs(rows, selection["max_frames"])
    return selected, {
        "returned_metadata": len(rows),
        "metadata_limit": 400,
        "possibly_truncated": True,
        "selection": "Temporally spread subset of overlapping locally saved native observations",
    }


def read_cached_original(row):
    artifact = Artifact.objects.get(pk=row["cached_original_id"], sequence_id=row["cached_parent_sequence"])
    raw = (settings.DATA_ROOT / artifact.filename).read_bytes()
    if len(raw) != artifact.size or hashlib.sha256(raw).hexdigest() != row["cached_original_sha256"]:
        raise ValueError("Cached native input checksum mismatch")
    return raw
