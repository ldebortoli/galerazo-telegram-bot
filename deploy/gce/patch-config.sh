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
credentials=/etc/galerazo/secrets/google-service-account.json
had_previous_env=no
had_previous_credentials=no
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
  if [[ "${had_previous_credentials}" == yes ]]; then
    sudo install -o root -g root -m 0600 "${credentials}.previous" "${credentials}"
  else
    sudo rm -f "${credentials}"
  fi
}
trap rollback_configuration ERR

sudo install -d -o root -g root -m 0700 /etc/galerazo /etc/galerazo/secrets
if sudo test -f "${bot_env}"; then
  sudo install -o root -g root -m 0600 "${bot_env}" "${bot_env}.previous"
  had_previous_env=yes
fi
if sudo test -f "${credentials}"; then
  sudo install -o root -g root -m 0600 "${credentials}" "${credentials}.previous"
  had_previous_credentials=yes
fi

sudo python3 - "${bot_env}" "${credentials}" "${patch_upload}" <<'PY'
import json
import os
from pathlib import Path
import sys

env_path = Path(sys.argv[1])
credentials_path = Path(sys.argv[2])
patch_path = Path(sys.argv[3])
env_keys = (
    "TELEGRAM_BOT_TOKEN",
    "OPENAI_API_KEY",
    "TELEGRAM_DEV_USER_IDS",
    "TELEGRAM_LOG_CHAT_ID",
    "TELEGRAM_ANNOUNCEMENTS_CHAT_ID",
    "DATABASE_PATH",
    "GOOGLE_SHEETS_CREDENTIALS_JSON_PATH",
    "GOOGLE_SHEETS_SPREADSHEET_ID",
    "GOOGLE_SHEETS_WORKSHEET_NAME",
)
editable_keys = set(env_keys) - {
    "DATABASE_PATH",
    "GOOGLE_SHEETS_CREDENTIALS_JSON_PATH",
}
credentials_key = "GOOGLE_SHEETS_CREDENTIALS_JSON"
allowed_keys = editable_keys | {credentials_key}

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
    if key == credentials_key:
        continue
    if not isinstance(value, str) or not value.strip():
        raise SystemExit("Los reemplazos deben ser textos no vacios")
    normalized = value.strip()
    if "\x00" in normalized or "\r" in normalized or "\n" in normalized:
        raise SystemExit("Una variable contiene caracteres no admitidos")
    if key == "TELEGRAM_BOT_TOKEN" and normalized == "replace-me":
        raise SystemExit("TELEGRAM_BOT_TOKEN conserva el placeholder")
    values[key] = normalized
for key in clear:
    if key != credentials_key:
        values[key] = ""

if credentials_key in updates:
    credentials_value = updates[credentials_key]
    if not isinstance(credentials_value, dict):
        raise SystemExit("La credencial de Google Sheets debe ser un objeto JSON")
    for required in ("type", "client_email", "private_key"):
        if not isinstance(credentials_value.get(required), str) or not credentials_value[required].strip():
            raise SystemExit("La credencial de Google Sheets esta incompleta")
    temporary_credentials = credentials_path.with_suffix(".json.next")
    temporary_credentials.write_text(
        json.dumps(credentials_value, separators=(",", ":")),
        encoding="utf-8",
    )
    os.chmod(temporary_credentials, 0o600)
    os.replace(temporary_credentials, credentials_path)
    values["GOOGLE_SHEETS_CREDENTIALS_JSON_PATH"] = "/app/secrets/google-service-account.json"
elif credentials_key in clear:
    credentials_path.unlink(missing_ok=True)
    values["GOOGLE_SHEETS_CREDENTIALS_JSON_PATH"] = ""

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
if sudo test -f "${credentials}"; then
  sudo chown root:root "${credentials}"
  sudo chmod 0600 "${credentials}"
fi
sudo bash /tmp/verify-host.sh --expect-configured >/dev/null
configuration_installed=yes
trap - ERR
echo "Credenciales remotas actualizadas; los valores no se muestran."
sudo bash /tmp/inspect-secrets.sh
