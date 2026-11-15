import pytest

from deploy.docker_run import persistent_secret


def test_secret_is_generated_once_and_survives_restart(tmp_path):
    path = tmp_path / 'state' / 'secret'
    first = persistent_secret(path)
    assert len(first) >= 64
    assert persistent_secret(path) == first


def test_existing_incomplete_secret_is_not_silently_replaced(tmp_path):
    path = tmp_path / 'secret'
    path.write_text('incomplete')
    with pytest.raises(ValueError, match='restore'):
        persistent_secret(path)
    assert path.read_text() == 'incomplete'
