"""Bounded reads of a fixed official FITS cube; never accept arbitrary URLs."""
import hashlib
import math
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .network import get


def download_cube(url, cache_dir=None, progress=None, max_seconds=210):
    # FITS extension lengths are derived from actual headers. The first header
    # probe does not assume a particular file byte length or table layout.
    from astropy.io import fits

    deadline = time.monotonic() + max_seconds
    cache = Path(cache_dir) / hashlib.sha256(url.encode()).hexdigest() if cache_dir else None
    if cache:
        cache.mkdir(parents=True, exist_ok=True)

    def read(start, end):
        part = cache / f'{start}-{end}.part' if cache else None
        checksum = part.with_suffix('.sha256') if part else None
        if part and part.is_file() and checksum.is_file():
            saved = part.read_bytes()
            if len(saved) == end-start+1 and hashlib.sha256(saved).hexdigest() == checksum.read_text().strip():
                return saved
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Cube transfer deadline reached')
        result = get(url, limit=end-start+1, max_seconds=remaining, byte_range=(start, end))
        if part:
            from science.imaging import atomic_write

            digest = atomic_write(part, result)
            atomic_write(checksum, digest.encode())
        return result

    offset = 0
    # Include the final WCS-WAVE lookup HDU. Omitting it leaves a seemingly
    # readable science array but breaks the cube's WAVE-TAB coordinate mapping.
    expected = [None, 'IMAGE', 'NHITS', 'FLAGS', 'SPECTRAL_CHANNELS', 'WCS-WAVE']
    for extension in expected:
        blocks = bytearray()
        while True:
            block = read(offset+len(blocks), offset+len(blocks)+2879)
            blocks.extend(block)
            if any(block[i:i+8] == b'END     ' for i in range(0, 2880, 80)):
                break
            if len(blocks) > 64 * 2880:
                raise ValueError('FITS header exceeds cube budget')
        header = fits.Header.fromstring(blocks.decode('ascii'))
        if header.get('EXTNAME') != extension:
            raise ValueError('Unexpected DR1 cube extension layout')
        count = math.prod(header.get(f'NAXIS{i}', 0) for i in range(1, header.get('NAXIS', 0)+1)) if header.get('NAXIS', 0) else 0
        size = (count * abs(header.get('BITPIX', 8)) // 8 + header.get('PCOUNT', 0)) * header.get('GCOUNT', 1)
        offset += len(blocks) + math.ceil(size/2880)*2880
        if offset > 384*1024*1024:
            raise ValueError('Cube exceeds 384 MiB budget')
    size = offset
    # Smaller complete ranges survive slow proxy connections; verified chunks
    # persist across failed jobs, while partial responses are never cached.
    chunk = 1024*1024
    ranges = [(start, min(start+chunk, size)-1) for start in range(0, size, chunk)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        parts = []
        received = 0
        for part in pool.map(lambda span: read(*span), ranges):
            parts.append(part)
            received += len(part)
            if progress:
                progress(received, size)
    raw = b''.join(parts)
    if len(raw) != size:
        raise ValueError('Incomplete cube transfer')
    return raw
