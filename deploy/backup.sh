#!/bin/sh
set -eu
dest="${1:?Usage: backup.sh absolute-backup-directory}"
mkdir -p "$dest"
docker compose exec -T db pg_dump -U argus -Fc argus > "$dest/database.dump"
docker compose exec -T web tar -C /app -czf - data > "$dest/artifacts.tar.gz"
sha256sum "$dest/database.dump" "$dest/artifacts.tar.gz" > "$dest/SHA256SUMS"
echo "Copy this backup to independent off-server storage. Restore rehearsal is required."
