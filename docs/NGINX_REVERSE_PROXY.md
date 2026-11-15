# Host Nginx reverse proxy

Use this profile when the VPS itself runs Nginx and Cloudflared is not wanted.

## Start Argus

```bash
docker compose -f compose.tunnel.yaml -f compose.nginx.yaml up --build -d
docker compose -f compose.tunnel.yaml -f compose.nginx.yaml ps
curl -I http://127.0.0.1:8080/health/
```

Cloudflared is in the `cloudflare` profile and is not started by this command.

## Nginx configuration

Create `/etc/nginx/sites-available/skyargus.space`:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name skyargus.space www.skyargus.space;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name skyargus.space www.skyargus.space;

    ssl_certificate /etc/letsencrypt/live/skyargus.space/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/skyargus.space/privkey.pem;

    client_max_body_size 512m;
    proxy_read_timeout 180s;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;
    proxy_pass_request_headers on;
    location / {
        proxy_pass http://127.0.0.1:8080;
    }
}
```

Enable it and obtain a certificate:

```bash
sudo ln -s /etc/nginx/sites-available/skyargus.space /etc/nginx/sites-enabled/skyargus.space
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d skyargus.space -d www.skyargus.space
```

Point DNS `A` records for the root and `www` to the VPS public IP. Do not configure Cloudflare Tunnel routes for this mode. Cloudflare DNS may remain proxied, but the origin must allow TCP 80/443 and Nginx must be listening there.

## Operations

```bash
docker compose -f compose.tunnel.yaml -f compose.nginx.yaml logs --tail=100 web proxy worker
docker compose -f compose.tunnel.yaml -f compose.nginx.yaml down
```

Do not use `down -v`; named volumes contain the database, reports, artifacts and persistent secret.
