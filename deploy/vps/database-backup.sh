#!/usr/bin/env bash
# Root-owned configuration only; never source application-controlled files.
set -Eeuo pipefail
umask 077
app="${1:?Usage: codex-database-backup <app>}"
[[ "$app" =~ ^[a-z][a-z0-9-]{0,31}$ ]] || exit 2
exec 9>/run/lock/codex-database-backup.lock
flock -w 7200 9
config="/etc/codex-backups/${app}.conf"
[[ -f "$config" && "$(stat -c %u "$config")" == 0 ]] || exit 2
[[ "$(stat -c %a "$config")" == 600 ]] || exit 2
# shellcheck source=/dev/null
source "$config"
directory="/srv/codex-backups/$app"
install -d -m 0700 "$directory"
day="$(TZ=America/Argentina/Buenos_Aires date +%Y%m%d)"
artifact="$directory/${app}-${day}.${BACKUP_FORMAT:?}"
receipt="$artifact.receipt.json"
if [[ "$BACKUP_FORMAT" == sqlite3 ]]; then
  source_args=(--source "${DATABASE_PATH:?}")
elif [[ "$BACKUP_FORMAT" == dump ]]; then
  source_args=()
  # No password in the command: PostgreSQL image already has its private env.
  if [[ ! -f "$artifact" ]]; then
    docker exec "${DATABASE_CONTAINER:?}" sh -ec 'exec pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"' > "$artifact.partial"
    docker exec -i "$DATABASE_CONTAINER" pg_restore --list < "$artifact.partial" >/dev/null
    mv "$artifact.partial" "$artifact"
  fi
else
  echo 'Unsupported database backup format.' >&2
  exit 2
fi
set -a
# shellcheck source=/dev/null
source /etc/codex-backups/telegram.env
set +a
/opt/codex-backups/venv/bin/python /opt/codex-backups/telegram_backup.py "$artifact" "$receipt" "${source_args[@]}"
# Only purge old artifacts after today's upload AND downloaded-copy verification.
find "$directory" -maxdepth 1 -type f -mtime +14 -delete
