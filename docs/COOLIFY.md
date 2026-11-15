# Deploy Argus to Coolify

**Proxy packaging:** deploy/Dockerfile.proxy copies the Nginx configuration into the proxy image. No host config-file bind mount is used; this avoids Coolify resolving a checkout-relative file against its persistent application directory and creating a directory at that path. Push both Dockerfiles and redeploy with a build after updates. Existing PostgreSQL/artifact/static volumes must be retained.

**Domain correction:** Django now uses ARGUS_DOMAIN (default skyargus.space) to form its public HTTPS origin. Coolify's SERVICE_URL_PROXY_80/SERVICE_FQDN_PROXY_80 may contain http and an internal port; these are used for routing, not Django host/origin settings. Keep proxy's Coolify domain set to HTTPS on internal port80. Change ARGUS_DOMAIN only to a plain hostname, without scheme, path or port. Expected runtime values: PUBLIC_URL=https://skyargus.space; CSRF_TRUSTED_ORIGINS=https://skyargus.space; ALLOWED_HOSTS includes skyargus.space without :80.

The repository includes a dedicated compose.coolify.yaml. Local Docker configuration and the older manual-TLS production configuration remain separate. No hand-edited certificate files or committed secrets are required.

## Click-through setup

1. Push this folder to your Git repository, including Dockerfile, compose.coolify.yaml and deploy/.
2. In Coolify choose New Resource → your Git repository → Docker Compose build pack. Select the desired branch.
3. Base Directory `/`; Docker Compose Location `/compose.coolify.yaml`. Use normal Coolify-managed deployment, not Raw mode.
4. Save/load configuration. Coolify generates SERVICE_PASSWORD_64_ARGUSSECRET and SERVICE_PASSWORD_64_ARGUSDB. Keep their values stable across deployments. If your Coolify version does not generate them automatically, populate each with a different64-character random alphanumeric secret in Environment Variables. Do not commit them.
5. Under Domains assign **proxy** an **HTTPS** root domain and internal port **80**. For a combined field use `https://argus.example.com:80`; visitors use `https://argus.example.com`. Point domain DNS at the deployment server. Enable HTTP→HTTPS redirection in Coolify.
6. Reload/save the parsed configuration so SERVICE_URL_PROXY_80 is the public HTTPS URL and SERVICE_FQDN_PROXY_80 its hostname. They automatically feed Django origin/host settings. These should be root URL/hostname values, not the container service name. Verify generated host excludes the routing port.
7. Click Deploy. Init checks configuration, migrates PostgreSQL and collects static files. Web and the database-backed worker start afterward; proxy starts once web is healthy. Init ending successfully is expected.

Only proxy receives a public domain. PostgreSQL, web and worker have no host-published ports. Coolify handles TLS. The internal Nginx passes the HTTPS forwarding header to Django to preserve secure sessions and avoid redirect loops.

## Resources and persistence

Use a Linux x86-64 Docker host compatible with requirements-linux.lock; allocate at least4GB RAM and adequate swap/headroom for scientific arrays/builds, plus10GB+ free disk initially. Each cached cube is about306MiB before additional transfer-cache copies. Monitor actual usage; this is not a measured capacity guarantee.

Three named volumes retain PostgreSQL, downloaded artifacts/transfer chunks and collected static assets. Do not remove these volumes during redeployment. Configure Coolify/server backups and test restoration separately. Existing Windows local.sqlite3/data are not automatically imported. Reports in the new installation belong to its new browser sessions.

This profile uses PostgreSQL with one database-polling worker; it deliberately does not require Redis/Celery. The separate legacy compose.yaml provides the alternative Celery stack. Do not start multiple polling workers without separate concurrency acceptance.

## Verify deployment

- Logs: db healthy; init exits0; web and proxy healthy; worker running.
- Public `/health/` responds; homepage loads CSS/JS; HTTP redirects to HTTPS without looping.
- Resolve/search a real field; worker moves queued→processing→ready, or shows a truthful upstream error.
- Save a test note/report and reopen; create/revoke a read-only share.
- Rebuild/redeploy and confirm database/artifacts persist.
- Test cube progress/resume on the server connection. No bundled private cache is supplied.

If init rejects the domain, configure HTTPS on proxy and reload configuration. If a POST returns403, compare generated SERVICE_URL_PROXY_80 with the exact browser origin. If login/session or redirects fail, inspect proxy forwarding settings and use one canonical HTTPS hostname. If jobs remain queued, inspect worker logs. Retain all secret values when rebuilding; changing the PostgreSQL password variable alone does not change an existing database user's password.

## Status

Compose YAML/service inheritance, required files and the startup validator were checked locally. Docker is unavailable on the authoring host: image builds, PostgreSQL/Linux execution and real Coolify deployment are **not runtime-verified**. Deployment still requires your Git connection, server and domain; no external publication was performed.

Official references: https://coolify.io/docs/applications/builds/docker-compose and https://coolify.io/docs/applications/configuration/persistent-storage.
