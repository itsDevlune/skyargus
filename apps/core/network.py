import io
import time
from urllib.parse import urljoin, urlsplit

import requests

HOSTS = {
    "irsa.ipac.caltech.edu",
    "ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca",
    "www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca",
    "gea.esac.esa.int",
    "simbad.cds.unistra.fr",
    "vizier.idia.ac.za",
    "alasky.cds.unistra.fr",
    "raw.githubusercontent.com",
    "api.github.com",
}
HOSTS.add("ws-uv.canfar.net")  # CADC's observed public data-storage redirect, verified 2026-11-15.
HOSTS.add("ws-sf.canfar.net")


def get(url, params=None, limit=32 * 1024 * 1024, redirects=0, max_seconds=None, byte_range=None):
    """Retry transient, idempotent archive reads with a finite attempt budget.

    A retry starts a fresh buffer; partial downloads are never concatenated.
    Validation failures, oversized responses and permanent HTTP errors fail fast.
    """
    deadline = time.monotonic() + max_seconds if max_seconds is not None else None
    for attempt in range(3):
        try:
            if deadline is not None and time.monotonic() >= deadline:
                raise requests.Timeout('Archive transfer time budget exhausted')
            return _get_once(url, params, limit, redirects, deadline, byte_range)
        except (requests.HTTPError, requests.Timeout, requests.ConnectionError) as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            transient = isinstance(exc, (requests.Timeout, requests.ConnectionError)) or status in (500, 502, 503, 504)
            if not transient or attempt == 2 or (deadline is not None and time.monotonic() >= deadline):
                raise
            time.sleep(2**attempt)


def _get_once(url, params=None, limit=32 * 1024 * 1024, redirects=0, deadline=None, byte_range=None):
    p = urlsplit(url)
    if p.scheme != "https" or p.hostname not in HOSTS or p.port not in (None, 443) or p.username or p.password:
        raise ValueError("Untrusted archive URL")
    headers = {"User-Agent": "Argus/0.1 bounded research client"}
    if byte_range is not None:
        headers['Range'] = f'bytes={byte_range[0]}-{byte_range[1]}'
    with requests.get(
        url,
        params=params,
        timeout=(8, min(60, max(1, deadline-time.monotonic()))) if deadline is not None else (8, 60),
        stream=True,
        allow_redirects=False,
        headers=headers,
    ) as r:
        r.raise_for_status()
        if byte_range is not None:
            prefix = f'bytes {byte_range[0]}-{byte_range[1]}/'
            if r.status_code != 206 or not r.headers.get('Content-Range', '').startswith(prefix):
                raise ValueError('Archive did not honor the requested FITS byte range')
        if r.is_redirect:
            if redirects >= 2:
                raise ValueError("Archive redirect limit exceeded")
            return _get_once(urljoin(r.url, r.headers["Location"]), limit=limit, redirects=redirects + 1, deadline=deadline)
        data = io.BytesIO()
        for block in r.iter_content(65536):
            if deadline is not None and time.monotonic() >= deadline:
                raise requests.Timeout('Archive transfer time budget exhausted')
            if data.tell() + len(block) > limit:
                raise ValueError("Archive response exceeds byte limit")
            data.write(block)
        result = data.getvalue()
        if byte_range is not None and len(result) != byte_range[1] - byte_range[0] + 1:
            raise ValueError('Incomplete archive byte range')
        return result
