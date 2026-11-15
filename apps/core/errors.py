"""Stable public explanations; keep provider URLs in provenance, not error banners."""

import requests


def archive_error(exc):
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    if status == 502:
        return {
            "code": "archive_temporarily_unavailable",
            "message": "Archive returned HTTP 502 (upstream service failure, not an Argus rate limit). Loaded observations are unchanged; retry when the archive recovers.",
            "retryable": True,
        }
    if status in (429, 500, 502, 503, 504):
        return {
            "code": "archive_temporarily_unavailable",
            "message": f"Archive temporarily unavailable (HTTP {status}). Your usable frames are preserved; retry later.",
            "retryable": True,
        }
    if isinstance(exc, (requests.Timeout, requests.ConnectionError, TimeoutError)):
        return {
            "code": "archive_connection_failed",
            "message": "Could not reach the archive within the time limit. Your usable frames are preserved; retry later.",
            "retryable": True,
        }
    return {
        "code": "observation_processing_failed",
        "message": str(exc).split(" for url:")[0][:240],
        "retryable": False,
    }
