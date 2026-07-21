#!/usr/bin/env bash
set -Eeuo pipefail

upload_dir="${1:-}"
if [[ -z "${upload_dir}" || ! -d "${upload_dir}" || -L "${upload_dir}" ]]; then
  echo "Directorio privado de carga invalido." >&2
  exit 1
fi
if [[ "$(stat -c '%u' "${upload_dir}")" != "$(id -u)" || "$(stat -c '%a' "${upload_dir}")" != "700" ]]; then
  echo "El directorio de carga no pertenece al usuario o no tiene modo 0700." >&2
  exit 1
fi

database_upload="${upload_dir}/galerazo.sqlite3"
if [[ ! -f "${database_upload}" || -L "${database_upload}" ]]; then
  echo "Falta el backup SQLite privado." >&2
  exit 1
fi
chmod 0600 "${database_upload}"

if [[ -n "$(sudo docker ps -q)" ]]; then
  echo "Hay un contenedor remoto activo; se rechazo reemplazar SQLite en uso." >&2
  exit 1
fi

check_integrity() {
  local database_path="$1"
  sudo python3 - "${database_path}" <<'PY'
import sqlite3
import sys

path = sys.argv[1]
connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
try:
    result = connection.execute("PRAGMA integrity_check").fetchone()[0]
finally:
    connection.close()
if result != "ok":
    raise SystemExit("SQLite integrity_check failed")
print("SQLITE_INTEGRITY=ok")
PY
}

check_integrity "${database_upload}"

database_dir=/srv/galerazo/data
backups_dir=/srv/galerazo/backups
database_path="${database_dir}/galerazo.sqlite3"
next_database="${database_dir}/galerazo.sqlite3.next"
previous_backup=""
had_previous=no
database_installed=no

rollback_database() {
  trap - ERR
  if [[ "${database_installed}" == yes ]]; then
    return
  fi
  if [[ "${had_previous}" == yes && -n "${previous_backup}" ]]; then
    sudo install -o 10001 -g 10001 -m 0600 "${previous_backup}" "${database_path}"
  else
    sudo rm -f "${database_path}"
  fi
  sudo rm -f "${next_database}"
}
trap rollback_database ERR

sudo install -d -o 10001 -g 10001 -m 0755 "${database_dir}" "${backups_dir}"
if sudo test -f "${database_path}"; then
  had_previous=yes
  previous_backup="${backups_dir}/galerazo-pre-migration-$(date -u +%Y%m%d-%H%M%S)-$$.sqlite3"
  sudo python3 - "${database_path}" "${previous_backup}" <<'PY'
import sqlite3
import sys

source = sqlite3.connect(sys.argv[1])
try:
    destination = sqlite3.connect(sys.argv[2])
    try:
        source.backup(destination)
    finally:
        destination.close()
finally:
    source.close()
PY
  sudo chown 10001:10001 "${previous_backup}"
  sudo chmod 0600 "${previous_backup}"
fi

sudo install -o 10001 -g 10001 -m 0600 "${database_upload}" "${next_database}"
check_integrity "${next_database}"
sudo mv -f "${next_database}" "${database_path}"
sudo chown 10001:10001 "${database_path}"
sudo chmod 0600 "${database_path}"
check_integrity "${database_path}"

database_installed=yes
trap - ERR
printf 'DATABASE_BYTES=%s\n' "$(sudo stat -c '%s' "${database_path}")"
echo "DATABASE_INSTALLED=yes"
