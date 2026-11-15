# Run Argus locally with Docker

Install Docker Desktop with Linux containers and Docker Compose v2. Allocate at least4GB memory and severalGB disk for scientific Python, the image build and downloaded cubes. This setup is local HTTP on loopback; it is not a public production deployment.

From the project/repository-copy folder:

```powershell
docker compose -f compose.local.yaml up --build -d
```

Open http://localhost:8000. No certificates or .env file are required. Init automatically migrates a fresh container database and collects static assets; the web/proxy and background worker start after init succeeds. First dependency download/build can take several minutes. Real archive searches/cube downloads require outbound HTTPS and remain subject to archive outages.

If your regular Django app already uses8000:

```powershell
$env:ARGUS_PORT = "8080"
docker compose -f compose.local.yaml up --build -d
```

Open http://localhost:8080. Use one hostname consistently to retain browser-session ownership.

## Check and manage

```powershell
docker compose -f compose.local.yaml ps -a
docker compose -f compose.local.yaml logs --tail=100 init web worker proxy
docker compose -f compose.local.yaml exec web python manage.py check
docker compose -f compose.local.yaml stop
docker compose -f compose.local.yaml start
docker compose -f compose.local.yaml down
```

`down` retains named volumes. Do not add `-v` unless you deliberately want to delete the container database, reports and downloaded data. The state volume contains /app/state/local.sqlite3 and /app/state/artifacts. Host local.sqlite3/data are excluded from the image and not imported automatically. Therefore existing host cache links may be unavailable in a fresh Docker installation; use explicit sky coordinates and retrieve real data. The static volume contains generated frontend assets.

For source updates run `docker compose -f compose.local.yaml up --build -d` again. Stop/start alone does not rebuild changed code. This local configuration uses one database worker and SQLite for small local usage; it does not establish production scalability. Existing compose.yaml/deploy/Dockerfile remain the separate PostgreSQL/Redis/Celery/TLS configuration requiring production secrets and certificates.

## Verification status

Docker executable is unavailable on the authoring Windows machine. Container build, Linux wheel installation, Nginx startup and end-to-end container workflow have NOT been executed here. On a Docker-enabled host first run `docker compose -f compose.local.yaml config`, then build/start and test search, worker progress, static assets, reports, restart persistence and cube retrieval using USER_TESTING_GUIDE.md. Do not report the Docker setup as runtime-verified until these checks pass.
