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

env_upload="${upload_dir}/bot.env"
credentials_upload="${upload_dir}/google-service-account.json"
if [[ ! -f "${env_upload}" || -L "${env_upload}" ]]; then
  echo "Falta el archivo privado bot.env." >&2
  exit 1
fi
chmod 0600 "${env_upload}"

token_count="$(grep -c '^TELEGRAM_BOT_TOKEN=' "${env_upload}" || true)"
database_count="$(grep -c '^DATABASE_PATH=/app/data/galerazo.sqlite3$' "${env_upload}" || true)"
if [[ "${token_count}" != "1" || "${database_count}" != "1" ]]; then
  echo "La configuracion remota no contiene las variables obligatorias esperadas." >&2
  exit 1
fi
if grep -Eq '^TELEGRAM_BOT_TOKEN=(|replace-me)$' "${env_upload}"; then
  echo "TELEGRAM_BOT_TOKEN esta vacio o conserva el placeholder." >&2
  exit 1
fi

had_previous_env=no
had_previous_credentials=no
credentials_installed=no
configuration_installed=no

rollback_configuration() {
  trap - ERR
  if [[ "${configuration_installed}" == yes ]]; then
    return
  fi
  if [[ "${had_previous_env}" == yes ]]; then
    sudo install -o root -g root -m 0600 /etc/galerazo/bot.env.previous /etc/galerazo/bot.env
  else
    sudo rm -f /etc/galerazo/bot.env
  fi
  if [[ "${had_previous_credentials}" == yes ]]; then
    sudo install -o root -g root -m 0600 \
      /etc/galerazo/secrets/google-service-account.json.previous \
      /etc/galerazo/secrets/google-service-account.json
  elif [[ "${credentials_installed}" == yes ]]; then
    sudo rm -f /etc/galerazo/secrets/google-service-account.json
  fi
}
trap rollback_configuration ERR

sudo install -d -o root -g root -m 0700 /etc/galerazo /etc/galerazo/secrets
if sudo test -f /etc/galerazo/bot.env; then
  sudo install -o root -g root -m 0600 \
    /etc/galerazo/bot.env /etc/galerazo/bot.env.previous
  had_previous_env=yes
fi
sudo install -o root -g root -m 0600 "${env_upload}" /etc/galerazo/bot.env

if [[ -f "${credentials_upload}" && ! -L "${credentials_upload}" ]]; then
  chmod 0600 "${credentials_upload}"
  if sudo test -f /etc/galerazo/secrets/google-service-account.json; then
    sudo install -o root -g root -m 0600 \
      /etc/galerazo/secrets/google-service-account.json \
      /etc/galerazo/secrets/google-service-account.json.previous
    had_previous_credentials=yes
  fi
  sudo install -o root -g root -m 0600 "${credentials_upload}" \
    /etc/galerazo/secrets/google-service-account.json
  credentials_installed=yes
fi

sudo bash /tmp/verify-host.sh --expect-configured
configuration_installed=yes
trap - ERR
echo "Configuracion remota instalada y validada sin mostrar secretos."
