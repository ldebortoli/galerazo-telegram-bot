#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script with sudo." >&2
  exit 1
fi
if [[ "$#" -ne 6 ]]; then
  echo "Usage: install-sqlite-backup.sh <bot-id> <database-path> <backup-dir> <bucket> <retention-days> <runtime-uid>" >&2
  exit 2
fi

bot_id="$1"
database_path="$2"
backup_dir="$3"
bucket="$4"
retention_days="$5"
runtime_uid="$6"

[[ "${bot_id}" =~ ^[a-z0-9][a-z0-9-]{0,62}$ ]] || { echo "Invalid bot id." >&2; exit 2; }
[[ "${database_path}" =~ ^/[A-Za-z0-9._/-]+$ && "${database_path}" != *".."* ]] || { echo "Invalid database path." >&2; exit 2; }
[[ "${backup_dir}" =~ ^/[A-Za-z0-9._/-]+$ && "${backup_dir}" != *".."* ]] || { echo "Invalid backup path." >&2; exit 2; }
[[ "${bucket}" =~ ^[a-z0-9][a-z0-9._-]{1,61}[a-z0-9]$ ]] || { echo "Invalid bucket." >&2; exit 2; }
[[ "${retention_days}" =~ ^[0-9]+$ && "${retention_days}" -ge 31 && "${retention_days}" -le 3650 ]] || { echo "Invalid retention." >&2; exit 2; }
[[ "${runtime_uid}" =~ ^[0-9]+$ && "${runtime_uid}" -ge 1 && "${runtime_uid}" -le 60000 ]] || { echo "Invalid runtime uid." >&2; exit 2; }
[[ -f "${database_path}" && ! -L "${database_path}" ]] || { echo "SQLite database not found." >&2; exit 1; }
[[ -f /tmp/bot-fleet-sqlite-backup.py && ! -L /tmp/bot-fleet-sqlite-backup.py ]] || { echo "Backup runtime was not uploaded." >&2; exit 1; }
command -v python3 >/dev/null || { echo "python3 is required." >&2; exit 1; }

runtime_account="bot-backup-${bot_id:0:19}"
if ! getent group "${runtime_uid}" >/dev/null; then
  groupadd --gid "${runtime_uid}" "${runtime_account}"
fi
if ! getent passwd "${runtime_uid}" >/dev/null; then
  useradd --uid "${runtime_uid}" --gid "${runtime_uid}" --no-create-home --home-dir /nonexistent \
    --shell /usr/sbin/nologin "${runtime_account}"
fi

program_dir=/usr/local/lib/bot-fleet-backup
config_dir=/etc/bot-fleet-backup
config_path="${config_dir}/${bot_id}.json"
unit_name="bot-fleet-sqlite-backup-${bot_id}"
service_path="/etc/systemd/system/${unit_name}.service"
timer_path="/etc/systemd/system/${unit_name}.timer"

install -d -o root -g root -m 0755 "${program_dir}" "${config_dir}"
install -d -o "${runtime_uid}" -g "${runtime_uid}" -m 0700 "${backup_dir}"
install -o root -g root -m 0755 /tmp/bot-fleet-sqlite-backup.py "${program_dir}/sqlite_backup.py"

config_tmp="$(mktemp "${config_dir}/.${bot_id}.XXXXXX")"
cleanup() {
  rm -f "${config_tmp}"
}
trap cleanup EXIT
python3 - "${config_tmp}" "${bot_id}" "${database_path}" "${backup_dir}" "${bucket}" "${retention_days}" <<'PY'
import json
import sys

path, bot_id, database_path, backup_dir, bucket, retention_days = sys.argv[1:]
payload = {
    "botId": bot_id,
    "databasePath": database_path,
    "localBackupDirectory": backup_dir,
    "bucket": bucket,
    "objectPrefix": f"bots/{bot_id}",
    "retentionDays": int(retention_days),
}
with open(path, "w", encoding="utf-8", newline="\n") as destination:
    json.dump(payload, destination, ensure_ascii=True, sort_keys=True)
    destination.write("\n")
PY
chown root:"${runtime_uid}" "${config_tmp}"
chmod 0640 "${config_tmp}"
mv -f "${config_tmp}" "${config_path}"

cat >"${service_path}" <<EOF
[Unit]
Description=Monthly consistent SQLite backup for ${bot_id}
Documentation=https://github.com/ldebortoli/galerazo-telegram-bot/blob/main/docs/BACKUPS_GCE.md
Wants=network-online.target
After=network-online.target
ConditionPathExists=${database_path}

[Service]
Type=oneshot
User=${runtime_uid}
Group=${runtime_uid}
UMask=0077
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/usr/bin/python3 ${program_dir}/sqlite_backup.py --config ${config_path}
Nice=10
TimeoutStartSec=15min
NoNewPrivileges=true
PrivateDevices=true
PrivateTmp=true
ProtectClock=true
ProtectControlGroups=true
ProtectHome=true
ProtectHostname=true
ProtectKernelLogs=true
ProtectKernelModules=true
ProtectKernelTunables=true
ProtectSystem=strict
ReadOnlyPaths=${database_path}
ReadWritePaths=${backup_dir}
LockPersonality=true
MemoryDenyWriteExecute=true
RestrictAddressFamilies=AF_INET AF_INET6
RestrictNamespaces=true
RestrictRealtime=true
RestrictSUIDSGID=true
SystemCallArchitectures=native
EOF

cat >"${timer_path}" <<EOF
[Unit]
Description=Monthly SQLite backup timer for ${bot_id}

[Timer]
OnCalendar=monthly
Persistent=true
RandomizedDelaySec=6h
AccuracySec=1h
Unit=${unit_name}.service

[Install]
WantedBy=timers.target
EOF

chmod 0644 "${service_path}" "${timer_path}"
systemctl daemon-reload
systemctl enable --now "${unit_name}.timer"
systemctl reset-failed "${unit_name}.service" 2>/dev/null || true
systemctl start "${unit_name}.service"
systemctl is-enabled "${unit_name}.timer"
systemctl is-active "${unit_name}.timer"
systemctl show "${unit_name}.timer" --property=NextElapseUSecRealtime --value
cat "${backup_dir}/last-backup-${bot_id}.json"
