"""Fail early with actionable setup errors, without printing secrets."""
import os
from urllib.parse import urlsplit


def validate(environment):
    public = urlsplit(environment.get('PUBLIC_URL', ''))
    if public.scheme != 'https' or not public.hostname or public.path not in ('', '/'):
        raise ValueError('In Coolify assign an HTTPS root domain to proxy on internal port80, then reload configuration.')
    allowed = environment.get('ALLOWED_HOSTS', '').split(',')
    if public.hostname not in allowed:
        raise ValueError('The proxy hostname must be in ALLOWED_HOSTS; reload the generated Coolify domain variables.')
    if len(environment.get('SECRET_KEY', '')) < 50:
        raise ValueError('Coolify must populate SERVICE_PASSWORD_64_ARGUSSECRET; do not use a placeholder secret.')
    database = urlsplit(environment.get('DATABASE_URL', ''))
    if database.scheme not in ('postgres', 'postgresql') or not database.password:
        raise ValueError('Coolify must populate SERVICE_PASSWORD_64_ARGUSDB and the PostgreSQL connection.')
    if environment.get('ARGUS_DEBUG') != '0':
        raise ValueError('Coolify production profile requires ARGUS_DEBUG=0.')


if __name__ == '__main__':
    try:
        validate(os.environ)
    except ValueError as error:
        raise SystemExit(str(error)) from None
    print('Coolify domain, secret and database configuration validated.')
