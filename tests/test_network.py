"""SSRF and network safeguard tests for the URL allowlist."""

import pytest

from apps.core.network import HOSTS, get


@pytest.mark.parametrize(
    "url,reason",
    [
        ("http://irsa.ipac.caltech.edu/file", "HTTP not HTTPS"),
        ("https://localhost/file", "localhost blocked"),
        ("https://127.0.0.1/file", "loopback blocked"),
        ("https://10.0.0.1/internal", "private range"),
        ("https://192.168.1.1/admin", "private range"),
        ("https://irsa.ipac.caltech.edu:444/file", "non-standard port"),
        ("https://user@irsa.ipac.caltech.edu/file", "credentials in URL"),
        ("https://evil.com/file", "unknown host"),
        ("ftp://irsa.ipac.caltech.edu/file", "wrong scheme"),
        ("https://user:pass@irsa.ipac.caltech.edu/file", "credentials in URL"),
        ("https://irsa.ipac.caltech.edu:80/file", "non-443 port"),
    ],
)
def test_ssrf_rejected(url, reason):
    with pytest.raises(ValueError, match="Untrusted"):
        get(url)


def test_allowed_hosts_include_expected():
    """Verify the allowlist contains the required archive hosts."""
    expected = {
        "irsa.ipac.caltech.edu",
        "gea.esac.esa.int",
        "ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca",
    }
    assert expected.issubset(HOSTS)


def test_allowlist_does_not_include_localhost():
    for h in HOSTS:
        assert "localhost" not in h.lower()
        assert h != "127.0.0.1"
        assert not h.startswith("10.")
        assert not h.startswith("192.168.")
