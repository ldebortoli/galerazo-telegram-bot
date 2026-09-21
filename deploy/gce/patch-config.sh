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

patch_upload="${upload_dir}/secret-patch.json"
if [[ ! -f "${patch_upload}" || -L "${patch_upload}" ]]; then
  echo "Falta el parche privado de credenciales." >&2
  exit 1
fi
chmod 0600 "${patch_upload}"

bot_env=/etc/galerazo/bot.env
had_previous_env=no
configuration_installed=no

rollback_configuration() {
  trap - ERR
  if [[ "${configuration_installed}" == yes ]]; then
    return
  fi
  if [[ "${had_previous_env}" == yes ]]; then
    sudo install -o root -g root -m 0600 "${bot_env}.previous" "${bot_env}"
  else
    sudo rm -f "${bot_env}"
  fi
}
trap rollback_configuration ERR

sudo install -d -o root -g root -m 0700 /etc/galerazo
if sudo test -f "${bot_env}"; then
  sudo install -o root -g root -m 0600 "${bot_env}" "${bot_env}.previous"
  had_previous_env=yes
fi
sudo python3 - "${bot_env}" "${patch_upload}" <<'PY'
import json
import os
from pathlib import Path
import sys

env_path = Path(sys.argv[1])
patch_path = Path(sys.argv[2])
env_keys = (
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_DEV_USER_IDS",
    "TELEGRAM_LOG_CHAT_ID",
    "TELEGRAM_ANNOUNCEMENTS_CHAT_ID",
    "TELEGRAM_HISOPO_COMMON_FILE_ID",
    "TELEGRAM_HISOPO_SILVER_FILE_ID",
    "TELEGRAM_HISOPO_GOLD_FILE_ID",
    "TELEGRAM_HISOPO_DIAMOND_FILE_ID",
    "TELEGRAM_HISOPO_FLEETING_FILE_ID",
    "TELEGRAM_HISOPO_MYSTERY_FILE_ID",
    "TELEGRAM_HISOPO_PUTRID_FILE_ID",
    "TELEGRAM_HISOPO_USED_FILE_ID",
    "TELEGRAM_HISOPO_RADIOACTIVE_FILE_ID",
    "TELEGRAM_HISOPO_BOMB_FILE_ID",
    "TELEGRAM_HISOPO_BOMB_DEFUSED_FILE_ID",
    "TELEGRAM_HISOPO_BOMB_EXPLODED_FILE_ID",
    "TELEGRAM_HISOPO_FRENETIC_FILE_ID",
    "TELEGRAM_HISOPO_BLACK_HOLE_FILE_ID",
    "TELEGRAM_HISOPO_EXPIRED_FILE_ID",
    "TELEGRAM_HISOPO_FAKE_FILE_ID",
    "TELEGRAM_HISOPO_TWIN_FILE_ID",
    "TELEGRAM_HISOPO_GIANT_FILE_ID",
    "TELEGRAM_HISOPO_MIRACLE_FILE_ID",
    "TELEGRAM_MINI_APP_URL",
    "TELEGRAM_MINI_APP_SHORT_NAME",
    "MINI_APP_BIND_HOST",
    "MINI_APP_PORT",
    "MINI_APP_PROXY_SECRET",
    "DATABASE_PATH",
    "GOOGLE_CLOUD_BILLING_PROJECT_ID",
    "GOOGLE_CLOUD_BILLING_TABLE",
    "GOOGLE_CLOUD_BILLING_REPORT_TIME",
)
allowed_keys = set(env_keys) - {"DATABASE_PATH"}

patch = json.loads(patch_path.read_text(encoding="utf-8"))
if not isinstance(patch, dict):
    raise SystemExit("El parche debe ser un objeto JSON")
updates = patch.get("updates", {})
clear = patch.get("clear", [])
if not isinstance(updates, dict) or not isinstance(clear, list):
    raise SystemExit("El parche no tiene el formato esperado")
if not updates and not clear:
    raise SystemExit("El parche no contiene cambios")
if any(not isinstance(key, str) or key not in allowed_keys for key in updates):
    raise SystemExit("El parche contiene una variable no permitida")
if any(not isinstance(key, str) or key not in allowed_keys for key in clear):
    raise SystemExit("El parche intenta limpiar una variable no permitida")
if len(set(clear)) != len(clear) or set(clear) & set(updates):
    raise SystemExit("El parche contiene operaciones duplicadas")
if "TELEGRAM_BOT_TOKEN" in clear:
    raise SystemExit("TELEGRAM_BOT_TOKEN no se puede eliminar")

values: dict[str, str] = {}
if env_path.is_file():
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        if not raw_line or raw_line.lstrip().startswith("#") or "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        values[key.strip()] = value.strip()
for key in env_keys:
    values.setdefault(key, "")

for key, value in updates.items():
    if not isinstance(value, str) or not value.strip():
        raise SystemExit("Los reemplazos deben ser textos no vacios")
    normalized = value.strip()
    if "\x00" in normalized or "\r" in normalized or "\n" in normalized:
        raise SystemExit("Una variable contiene caracteres no admitidos")
    if key == "TELEGRAM_BOT_TOKEN" and normalized == "replace-me":
        raise SystemExit("TELEGRAM_BOT_TOKEN conserva el placeholder")
    values[key] = normalized
for key in clear:
    values[key] = ""

values["DATABASE_PATH"] = "/app/data/galerazo.sqlite3"
token = values.get("TELEGRAM_BOT_TOKEN", "")
if not token or token == "replace-me":
    raise SystemExit("TELEGRAM_BOT_TOKEN debe permanecer configurado")

temporary_env = env_path.with_suffix(".env.next")
temporary_env.write_text(
    "".join(f"{key}={values[key]}\n" for key in env_keys),
    encoding="utf-8",
)
os.chmod(temporary_env, 0o600)
os.replace(temporary_env, env_path)
PY

sudo chown root:root "${bot_env}"
sudo chmod 0600 "${bot_env}"
sudo bash /tmp/verify-host.sh --expect-configured >/dev/null
configuration_installed=yes
trap - ERR
echo "Credenciales remotas actualizadas; los valores no se muestran."
sudo bash /tmp/inspect-secrets.sh
