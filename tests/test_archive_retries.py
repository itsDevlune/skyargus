from unittest.mock import MagicMock, patch

import pytest
import requests

from apps.core.network import get


def http_error(status):
    response = requests.Response()
    response.status_code = status
    return requests.HTTPError(response=response)


def test_transient_502_retries_then_returns_original_bytes():
    with patch("apps.core.network._get_once", side_effect=[http_error(502), b"real archive bytes"]) as fetch, patch("apps.core.network.time.sleep") as sleep:
        assert get("https://irsa.ipac.caltech.edu/SIA", {"MAXREC": 100}) == b"real archive bytes"
    assert fetch.call_count == 2
    sleep.assert_called_once_with(1)


def test_outage_is_bounded_and_preserves_final_error():
    error = http_error(502)
    with patch("apps.core.network._get_once", side_effect=error) as fetch, patch("apps.core.network.time.sleep") as sleep:
        with pytest.raises(requests.HTTPError) as caught:
            get("https://irsa.ipac.caltech.edu/SIA")
    assert caught.value is error
    assert fetch.call_count == 3
    assert [call.args[0] for call in sleep.call_args_list] == [1, 2]


@pytest.mark.parametrize("error", [http_error(404), http_error(429), ValueError("Untrusted archive URL"), ValueError("Archive response exceeds byte limit")])
def test_permanent_or_rate_limited_responses_are_not_retried(error):
    with patch("apps.core.network._get_once", side_effect=error) as fetch, patch("apps.core.network.time.sleep") as sleep:
        with pytest.raises(type(error)):
            get("https://irsa.ipac.caltech.edu/SIA")
    assert fetch.call_count == 1
    sleep.assert_not_called()


def test_exact_range_bytes_are_validated():
    response = MagicMock()
    response.status_code = 206
    response.is_redirect = False
    response.headers = {'Content-Range': 'bytes 10-13/100'}
    response.iter_content.return_value = [b'abcd']
    response.__enter__.return_value = response
    with patch('apps.core.network.requests.get', return_value=response) as fetch:
        assert get('https://irsa.ipac.caltech.edu/file.fits', byte_range=(10, 13), limit=4) == b'abcd'
    assert fetch.call_args.kwargs['headers']['Range'] == 'bytes=10-13'


def test_ignored_range_does_not_accept_whole_file():
    response = MagicMock()
    response.status_code = 200
    response.__enter__.return_value = response
    with patch('apps.core.network.requests.get', return_value=response):
        with pytest.raises(ValueError, match='honor'):
            get('https://irsa.ipac.caltech.edu/file.fits', byte_range=(10, 13), limit=4)
