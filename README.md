# Argus

**Standalone VPS + Cloudflare:** put `CLOUDFLARE_TUNNEL_TOKEN` in `.env`, then run `docker compose -f compose.tunnel.yaml up --build -d`. Configure the tunnel hostname `skyargus.space` to service `proxy:80`. See [docs/CLOUDFLARED.md](docs/CLOUDFLARED.md). Docker runtime verification is still pending on a Docker-enabled host.

**Host Nginx instead of Cloudflare Tunnel:** run the overlay `docker compose -f compose.tunnel.yaml -f compose.nginx.yaml up --build -d`, then configure the VPS Nginx reverse proxy as described in [docs/NGINX_REVERSE_PROXY.md](docs/NGINX_REVERSE_PROXY.md).

**Coolify:** select the Docker Compose build pack and `/compose.coolify.yaml`, then assign an HTTPS domain to the `proxy` service (internal port80). Coolify generates the two secrets. Setup and deployment checks: [docs/COOLIFY.md](docs/COOLIFY.md). Docker/Coolify runtime verification has not been performed on this authoring machine.

A working Django workspace for real infrared sky observations and reproducible evidence. **Development build; the full requested release is not complete.**

Use [local run instructions](docs/DEPLOYMENT.md), [feature evidence](docs/FEATURES.md), [tests](docs/TEST_PLAN.md), [source integrations](docs/RESOURCE_INTEGRATION.md) and [continuation checkpoint](docs/PROGRESS.md).

```powershell
.venv313/Scripts/python manage.py runserver 127.0.0.1:8000
# Separate terminal
.venv313/Scripts/python manage.py workjobs
```

Open http://127.0.0.1:8000. Real cached example: RA 269.452075°, Dec +4.693391°, 6×6 arcmin, SPHEREx DR1 detector 3. No fake sky or initial autoplay. Private notes belong to this browser session; export immutable reports before clearing cookies.

Verified: 29 pytest tests, 3 Playwright shell tests, real dated SPHEREx browser workflow, actual Gaia DR3 query and separate NEOSSat native raw FITS sequence. Screenshots in [docs/evidence](docs/evidence). Docker production configuration is prepared but Linux/PostgreSQL/Celery/restore are not yet tested. Calibrated spectra, composites, scientific stacks/differences, WISE imagery and other inventory items remain unfinished.
