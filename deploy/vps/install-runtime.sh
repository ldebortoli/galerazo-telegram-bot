#!/usr/bin/env bash
# Run from a private source bundle with deploy/vps and galerazo_bot intact.
set -Eeuo pipefail
umask 077
[[ $EUID == 0 ]] || exit 2
directory="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$directory/../.." && pwd)"
test -s /etc/galerazo/cloudflared.token
test -s /etc/codex-backups/telegram.env
install -d -m 0700 /opt/codex-backups /srv/codex-backups
DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv
python3 -m venv /opt/codex-backups/venv
/opt/codex-backups/venv/bin/python -m pip install --disable-pip-version-check -r "$directory/backup-requirements.txt"
install -m 0644 "$root/galerazo_bot/telegram_backup.py" /opt/codex-backups/telegram_backup.py
install -m 0755 "$directory/database-backup.sh" /usr/local/sbin/codex-database-backup
install -m 0644 "$directory/systemd/"codex-backup@.* /etc/systemd/system/
install -m 0644 "$directory/tunnel.yaml" /opt/galerazo/tunnel.yaml
chown 65532:65532 /etc/galerazo/cloudflared.token
chmod 0400 /etc/galerazo/cloudflared.token
if [[ ! -f /etc/galerazo/google-sheets.json ]]; then
  printf '{}' > /etc/galerazo/google-sheets.json
  chown 10001:10001 /etc/galerazo/google-sheets.json
  chmod 0400 /etc/galerazo/google-sheets.json
fi
systemd-analyze verify /etc/systemd/system/codex-backup@.service /etc/systemd/system/codex-backup@.timer
systemctl daemon-reload
docker compose -f /opt/galerazo/tunnel.yaml up -d
# Enable each per-app timer only after its live database/config/restore test exists.
