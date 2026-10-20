#!/usr/bin/env bash
# Local images arrive over authenticated SSH; no external registry or GCP.
set -Eeuo pipefail
umask 077
[[ $EUID == 0 && $# == 1 ]] || exit 2
image="$1"
[[ "$image" =~ ^galerazo-bot:[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$ ]] || exit 2
exec 8>/run/lock/galerazo-deploy.lock
flock -n 8
cd /opt/galerazo
test -s /etc/galerazo/bot.env
test -s /srv/galerazo/data/galerazo.sqlite3
docker image inspect "$image" --format '{{.Id}}' >/dev/null
docker run --rm --network none --read-only --memory 128m --memory-swap 128m \
  --cgroup-parent apps-galerazo.slice --env-file /etc/galerazo/bot.env \
  -e DATABASE_PATH=/app/data/galerazo.sqlite3 \
  -v /srv/galerazo/data:/app/data:ro "$image" python -m galerazo_bot.healthcheck
old=''
candidate_attempted=no
snapshot="/srv/galerazo/backups/predeploy-$(date -u +%Y%m%dT%H%M%SZ).sqlite3"
recover_previous() {
  local result=$?
  trap - ERR
  if [[ "$candidate_attempted" == yes ]]; then
    # Never replace SQLite while a candidate may still be writing it.
    if ! docker compose --env-file image.env -f compose.yaml stop bot; then
      echo 'Cannot stop failed candidate; database left intact for operator recovery.' >&2
      exit "$result"
    fi
    rm -f /srv/galerazo/data/galerazo.sqlite3-wal /srv/galerazo/data/galerazo.sqlite3-shm
    install -o 10001 -g 10001 -m 0600 "$snapshot" /srv/galerazo/data/restore.next
    mv -f /srv/galerazo/data/restore.next /srv/galerazo/data/galerazo.sqlite3
  fi
  if [[ -n "$old" ]]; then
    printf 'GALERAZO_IMAGE=%s\n' "$old" > image.env
    docker compose --env-file image.env -f compose.yaml up -d --wait --wait-timeout 150
  fi
  echo 'Deploy failed; previous image restarted when available. Database restored only after a failed candidate was stopped.' >&2
  exit "$result"
}
if [[ -f image.env ]]; then
  old="$(sed -n 's/^GALERAZO_IMAGE=//p' image.env)"
fi
trap recover_previous ERR
if [[ -n "$old" ]]; then
  docker compose --env-file image.env -f compose.yaml stop bot
fi
/opt/codex-backups/venv/bin/python - "$snapshot" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0,'/opt/codex-backups')
from telegram_backup import snapshot_sqlite
snapshot_sqlite(Path('/srv/galerazo/data/galerazo.sqlite3'),Path(sys.argv[1]))
PY
if [[ -n "$old" && "$old" != "$image" ]]; then cp image.env previous-image.env; fi
printf 'GALERAZO_IMAGE=%s\n' "$image" > image.env
candidate_attempted=yes
if docker compose --env-file image.env -f compose.yaml up -d --wait --wait-timeout 150; then
  trap - ERR
  docker compose --env-file image.env -f compose.yaml ps
  echo "Deploy healthy: $image; database snapshot: $snapshot"
  exit 0
fi
# Trigger the same recovery path used by snapshot/configuration failures.
false
