"""Bounded opt-in real archive acceptance; never used by offline CI.

Run with .venv313/Scripts/python.exe scripts/verify-real-cube.py.
Only operates on the explicitly named cube-verification job.
"""
# ruff: noqa: E402
import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'argus.settings')

import django

django.setup()

import numpy as np
from astropy.io import fits
from django.conf import settings
from PIL import Image

from apps.core.models import Artifact, Job
from apps.core.tasks import run_job
from science.cubes import channel_png, pixel_spectrum, sky_spectrum


def main():
    job = Job.objects.get(pk='09448973-eb30-4036-b801-9847cb56770a', owner='cube-verification', kind='cube')
    for attempt in range(4):
        # A prior verification process may still own the first transfer.
        deadline = time.monotonic() + 250
        while job.state == 'running' and time.monotonic() < deadline:
            time.sleep(2)
            job.refresh_from_db()
        if job.state == 'completed':
            break
        if job.state == 'running':
            raise RuntimeError('Existing verification attempt still running; do not steal its lease')
        print(f'Resuming bounded verification attempt {attempt+1}', flush=True)
        job.state = 'queued'
        job.save(update_fields=['state'])
        run_job(str(job.id))
        job.refresh_from_db()
    if job.state != 'completed':
        raise RuntimeError(f'Real transfer still blocked: {job.error}')

    info = job.result
    artifact = Artifact.objects.get(pk=info['artifact']['id'])
    path = settings.DATA_ROOT / artifact.filename
    with path.open('rb') as original:
        assert hashlib.file_digest(original, 'sha256').hexdigest() == artifact.sha256
    assert len(info['channels']) == 102
    with fits.open(path, memmap=False) as hdus:
        image = hdus['IMAGE'].data
        hits = hdus['NHITS'].data
        assert image.shape == (102, 512, 512)
        spectrum = pixel_spectrum(path, 256, 256)
        assert len(spectrum['measurements']) == 102
        for i, sample in enumerate(spectrum['measurements']):
            valid = np.isfinite(image[i, 256, 256]) and hits[i, 256, 256] > 0
            assert sample['available'] == bool(valid)
            assert sample['surface_brightness'] == (float(image[i, 256, 256]) if valid else None)
            assert sample['wavelength_um'] == float(hdus['SPECTRAL_CHANNELS'].data['WAVELENGTH'][i])
            assert sample['flags'] == int(hdus['FLAGS'].data[i, 256, 256])
        plane = next(c['index'] for c in info['channels'] if c['available'])
        coverage = Image.open(io.BytesIO(channel_png(path, plane, coverage=True)))
        alpha = np.array(coverage)[..., 3]
        np.testing.assert_array_equal(alpha[::-1] > 0, np.isfinite(image[plane]) & (hits[plane] > 0))
        source = sky_spectrum(path, 269.452075, 4.693391)
        x, y = source['pixel']['x'], source['pixel']['y']
        for i, sample in enumerate(source['measurements']):
            if sample['available']:
                assert sample['surface_brightness'] == float(image[i, y, x])
    evidence = ROOT / 'docs/evidence/real-cube'
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence/'metadata.json').write_text(json.dumps(info, indent=2))
    (evidence/'pixel-spectrum.json').write_text(json.dumps(spectrum, indent=2))
    (evidence/'source-spectrum.json').write_text(json.dumps(source, indent=2))
    (evidence/'channel.png').write_bytes(channel_png(path, plane))
    (evidence/'coverage.png').write_bytes(channel_png(path, plane, coverage=True))
    print(json.dumps({'cube_id': info['cube_id'], 'shape': image.shape,
                      'available_channels': sum(c['available'] for c in info['channels']),
                      'unavailable': [c['index']+1 for c in info['channels'] if not c['available']],
                      'all_102_samples_match_original': True, 'coverage_matches_original': True}), flush=True)


if __name__ == '__main__':
    main()
