"""Standalone container launcher; create one persistent secret before Django."""
import os
import secrets
import sys
from pathlib import Path


def persistent_secret(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        value = path.read_text().strip()
        if len(value) < 50:
            raise ValueError('Persistent application secret is incomplete; restore it from backup before starting.')
        return value
    value = secrets.token_urlsafe(64)
    with os.fdopen(descriptor, 'w') as output:
        output.write(value)
        output.flush()
        os.fsync(output.fileno())
    return value


def main():
    if not os.environ.get('SECRET_KEY'):
        os.environ['SECRET_KEY'] = persistent_secret('/app/state/django-secret')
    command = sys.argv[1:]
    if not command:
        raise SystemExit('Supply a container command.')
    os.execvp(command[0], command)


if __name__ == '__main__':
    main()
