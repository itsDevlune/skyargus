# Argus on a VPS with Cloudflare Tunnel

This profile runs Argus without Coolify and publishes it through a stable named Cloudflare Tunnel at `skyargus.space`. No host ports are exposed; the internal route is `cloudflared -> proxy:80 -> web:8000`.

## One-time Cloudflare setup

1. In Cloudflare Zero Trust, create a tunnel and choose **Docker**.
2. Copy the token shown by Cloudflare.
3. In the tunnel's **Public Hostnames**, add hostname `skyargus.space`, service type `HTTP`, URL `proxy:80`. Add `www.skyargus.space` similarly if required. Cloudflare creates the tunnel CNAME; do not add an A record for the tunnel hostname pointing at the VPS.

## VPS deployment

```bash
git clone <your-repository-url> argus
cd argus
cp .env.example .env
```

Edit `.env` and add `CLOUDFLARE_TUNNEL_TOKEN=...` (keep it private), then run:

```bash
docker compose -f compose.tunnel.yaml up --build -d
docker compose -f compose.tunnel.yaml ps
docker compose -f compose.tunnel.yaml logs -f cloudflared
```

Open `https://skyargus.space`. Expected services: `web` healthy, `worker` running, `proxy` healthy and `cloudflared` running.

## Checks and maintenance

```bash
docker compose -f compose.tunnel.yaml exec web python deploy/docker_run.py python manage.py check
docker compose -f compose.tunnel.yaml logs --tail=100 web worker proxy cloudflared
docker compose -f compose.tunnel.yaml restart cloudflared
docker compose -f compose.tunnel.yaml down
```

`down` preserves named volumes. Do not use `down -v` unless intentionally erasing SQLite, reports, downloaded artifacts and the persistent Django secret. Back up the `argus-tunnel_state` volume before upgrades. This SQLite/one-worker profile is intended for small installations. Never commit the tunnel token.

Docker and Cloudflare runtime startup were not available on the authoring workstation; run the checks above on the VPS before treating deployment as verified.
