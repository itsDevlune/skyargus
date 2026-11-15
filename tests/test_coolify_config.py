import pytest

from deploy.check_coolify import validate


def configured():
    return {
        'PUBLIC_URL': 'https://argus.example.com',
        'ALLOWED_HOSTS': 'localhost,127.0.0.1,web,argus.example.com',
        'SECRET_KEY': 'a' * 64,
        'DATABASE_URL': 'postgres://argus:password@db:5432/argus',
        'ARGUS_DEBUG': '0',
    }


def test_complete_coolify_configuration_validates():
    validate(configured())


@pytest.mark.parametrize('key,value', [
    ('PUBLIC_URL', 'http://argus.example.com'),
    ('PUBLIC_URL', 'https://argus.example.com/subpath'),
    ('ALLOWED_HOSTS', 'localhost'),
    ('SECRET_KEY', 'placeholder'),
    ('DATABASE_URL', 'sqlite:///local.sqlite3'),
    ('ARGUS_DEBUG', '1'),
])
def test_incomplete_coolify_configuration_is_actionable(key, value):
    environment = configured()
    environment[key] = value
    with pytest.raises(ValueError):
        validate(environment)
