#!/usr/bin/env bash
set -Eeuo pipefail

expected_state=any
case "${1:-}" in
  "") ;;
  --expect-pristine) expected_state=pristine ;;
  --expect-configured) expected_state=configured ;;
  *)
    echo "Uso: $0 [--expect-pristine|--expect-configured]" >&2
    exit 2
    ;;
esac

if [[ ${EUID} -ne 0 ]]; then
  echo "Este script debe ejecutarse como root." >&2
  exit 1
fi

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Falta el comando requerido: $1" >&2
    exit 1
  fi
}

check_path() {
  local path="$1"
  local expected_mode="$2"
  local expected_owner="$3"
  local actual_mode actual_owner

  if [[ ! -e "${path}" ]]; then
    echo "Falta la ruta requerida: ${path}" >&2
    exit 1
  fi

  actual_mode="$(stat -c '%a' "${path}")"
  actual_owner="$(stat -c '%u:%g' "${path}")"
  if [[ "${actual_mode}" != "${expected_mode}" || "${actual_owner}" != "${expected_owner}" ]]; then
    echo "Permisos invalidos en ${path}: ${actual_mode} ${actual_owner}" >&2
    exit 1
  fi

  printf 'PERM=%s OWNER=%s PATH=%s\n' "${actual_mode}" "${actual_owner}" "${path}"
}

require_command docker
require_command gcloud

docker_active="$(systemctl is-active docker)"
docker_enabled="$(systemctl is-enabled docker)"
[[ "${docker_active}" == "active" ]]
[[ "${docker_enabled}" == "enabled" ]]
printf 'DOCKER_ACTIVE=%s\n' "${docker_active}"
printf 'DOCKER_ENABLED=%s\n' "${docker_enabled}"
docker version --format 'DOCKER_SERVER={{.Server.Version}} ARCH={{.Server.Arch}}'
docker compose version
printf 'GCLOUD='; gcloud --version | sed -n '1p'

check_path /opt/galerazo 755 0:0
check_path /srv/galerazo/data 755 10001:10001
check_path /srv/galerazo/backups 755 10001:10001
check_path /etc/galerazo 700 0:0
check_path /etc/galerazo/secrets 700 0:0
check_path /etc/galerazo/bot.env 600 0:0

token_line_count="$(grep -c '^TELEGRAM_BOT_TOKEN=' /etc/galerazo/bot.env || true)"
if [[ "${token_line_count}" != "1" ]]; then
  echo "bot.env debe contener exactamente una variable TELEGRAM_BOT_TOKEN." >&2
  exit 1
fi
if grep -qx 'TELEGRAM_BOT_TOKEN=' /etc/galerazo/bot.env; then
  token_state=empty
elif grep -qx 'TELEGRAM_BOT_TOKEN=replace-me' /etc/galerazo/bot.env; then
  token_state=placeholder
else
  token_state=configured
fi
printf 'TOKEN_STATE=%s\n' "${token_state}"

container_count="$(docker ps -aq | wc -l | tr -d ' ')"
image_count="$(docker images -q | sort -u | wc -l | tr -d ' ')"
database_present=no
compose_present=no
[[ -e /srv/galerazo/data/galerazo.sqlite3 ]] && database_present=yes
[[ -e /opt/galerazo/compose.yaml ]] && compose_present=yes
printf 'CONTAINERS=%s\n' "${container_count}"
printf 'IMAGES=%s\n' "${image_count}"
printf 'DATABASE_PRESENT=%s\n' "${database_present}"
printf 'COMPOSE_PRESENT=%s\n' "${compose_present}"

if [[ "${expected_state}" == pristine ]]; then
  [[ "${token_state}" == "placeholder" ]]
  [[ "${container_count}" == "0" ]]
  [[ "${image_count}" == "0" ]]
  [[ "${database_present}" == "no" ]]
  [[ "${compose_present}" == "no" ]]
  echo 'PRISTINE_STATE=yes'
elif [[ "${expected_state}" == configured ]]; then
  [[ "${token_state}" == "configured" ]]
  echo 'CONFIGURED_STATE=yes'
fi

df -h /
free -m
