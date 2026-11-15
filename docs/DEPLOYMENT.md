# Deployment status and commands
Local working development application; production package prepared, **not production-tested or externally deployed**. Docker is absent on this Windows host. No domain/TLS credentials or target-server access supplied. Linux testing, Postgres/Redis/Celery execution and backup restore are therefore unverified, not passed.

Local Windows:
```powershell
uv python install 3.13
uv venv .venv313 --python 3.13
uv pip install --python .venv313/Scripts/python.exe --require-hashes -r requirements.lock
npm ci
npm run build
.venv313/Scripts/python manage.py migrate
.venv313/Scripts/python manage.py runserver 127.0.0.1:8000
# Separate terminal (database-polling local worker):
.venv313/Scripts/python manage.py workjobs
```
Open http://127.0.0.1:8000. Set detector 3 and explicit 269.452075 / 4.693391, 6×6 arcmin for the verified cached field. Use live resolver for names, remembering reference-epoch limitations. Existing local SQLite and data/ hold downloaded evidence and are intentionally gitignored.

On a Linux machine with Docker Compose: copy .env.example to .env; generate real strong secrets; set host/domain; put TLS fullchain.pem/privkey.pem in deploy/certs (never commit private keys); run docker compose build. Run docker compose run --rm web python manage.py migrate and docker compose run --rm web python manage.py collectstatic --noinput before docker compose up -d. Run production system checks and test health/HTTPS/job/report/share flows. Do not expose database/Redis ports. Source static files shared with Nginx; artifact data shared with web/worker. Migration service orchestration is manual until rehearsed.

Images currently use mutable upstream tags. Pin validated base-image digests before release. Lock files are separately resolved for Windows and Linux; this is not clean Linux wheel validation. Gunicorn's normal HTTP path remains short; astronomy runs in worker concurrency 1 with BLAS threads 1. Resource limits and visitor capacity require measurements, not the VPS planning estimate.
