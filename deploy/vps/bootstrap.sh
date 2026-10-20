#!/usr/bin/env bash
# Existing Debian/Ubuntu host only. Never creates billable cloud resources.
set -Eeuo pipefail
[[ "$EUID" -eq 0 ]] || { echo 'Run as root.' >&2; exit 1; }
. /etc/os-release
case "$ID" in ubuntu|debian) ;; *) echo 'Only Debian/Ubuntu supported.' >&2; exit 1 ;; esac
[[ -f /sys/fs/cgroup/cgroup.controllers ]] || {
  echo 'cgroup v2 required; no kernel changes or restart performed.' >&2; exit 1;
}
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y docker.io docker-compose-v2 python3 ca-certificates sqlite3
systemctl enable --now docker
[[ "$(docker info --format '{{.CgroupDriver}}')" == systemd ]] || {
  echo 'Docker requires the systemd cgroup driver; existing configuration unchanged.' >&2; exit 1;
}
install -d -m 0755 /opt/galerazo /srv/galerazo/data /srv/galerazo/backups
install -d -m 0700 /etc/galerazo /etc/codex-backups /srv/codex-backups
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
install -m 0644 "$script_dir"/systemd/*.slice /etc/systemd/system/
systemctl daemon-reload
systemctl start apps.slice apps-galerazo.slice apps-tivio.slice apps-altura.slice apps-enlamisma.slice apps-backups.slice
chown 10001:10001 /srv/galerazo/data /srv/galerazo/backups
docker compose version
systemctl show apps-galerazo.slice apps-tivio.slice apps-altura.slice apps-enlamisma.slice -p Id -p MemoryMax -p MemorySwapMax
