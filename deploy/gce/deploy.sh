#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script with sudo." >&2
  exit 1
fi
if [[ "$#" -ne 1 ]]; then
  echo "Usage: deploy.sh <artifact-registry-image>" >&2
  exit 2
fi

new_image="$1"
if [[ ! "${new_image}" =~ ^[A-Za-z0-9][A-Za-z0-9._/:@-]+$ ]]; then
  echo "Invalid image reference." >&2
  exit 2
fi

app_dir=/opt/galerazo
compose_file="${app_dir}/compose.yaml"
image_env="${app_dir}/image.env"
previous_env="${app_dir}/previous-image.env"
bot_env=/etc/galerazo/bot.env

if [[ ! -f "${bot_env}" ]]; then
  echo "Missing ${bot_env}; run bootstrap.sh first." >&2
  exit 1
fi
if grep -Eq '^TELEGRAM_BOT_TOKEN=(replace-me)?$' "${bot_env}"; then
  echo "Configure TELEGRAM_BOT_TOKEN in ${bot_env} before deploying." >&2
  exit 1
fi

install -d -m 0755 "${app_dir}"

registry_host="${new_image%%/*}"
if [[ "${registry_host}" == *.pkg.dev ]]; then
  gcloud auth configure-docker "${registry_host}" --quiet
fi

old_image=""
if [[ -f "${image_env}" ]]; then
  old_image="$(sed -n 's/^GALERAZO_IMAGE=//p' "${image_env}" | head -n 1)"
fi

if [[ -n "${old_image}" ]]; then
  if [[ -f "${compose_file}" ]] && docker compose --env-file "${image_env}" -f "${compose_file}" \
      ps --status running --services | grep -qx bot; then
    docker compose --env-file "${image_env}" -f "${compose_file}" \
      exec -T bot python -m galerazo_bot.deploy_backup
  fi
  cp "${image_env}" "${previous_env}"
fi

install -m 0644 /tmp/galerazo-compose.yaml "${compose_file}"
install -m 0755 /tmp/galerazo-deploy.sh "${app_dir}/deploy.sh"
install -m 0755 /tmp/galerazo-rollback.sh "${app_dir}/rollback.sh"

echo "Pulling ${new_image}..."
GALERAZO_IMAGE="${new_image}" docker compose -f "${compose_file}" pull bot
printf 'GALERAZO_IMAGE=%s\n' "${new_image}" > "${image_env}"
chmod 0600 "${image_env}"

echo "Starting Galerazo Bot..."
if docker compose --env-file "${image_env}" -f "${compose_file}" \
    up -d --remove-orphans --wait --wait-timeout 120; then
  docker compose --env-file "${image_env}" -f "${compose_file}" ps
  echo "Deploy completed: ${new_image}"
  exit 0
fi

echo "The new container did not become healthy." >&2
if [[ -n "${old_image}" && -f "${previous_env}" ]]; then
  echo "Restoring ${old_image}..." >&2
  cp "${previous_env}" "${image_env}"
  docker compose --env-file "${image_env}" -f "${compose_file}" \
    up -d --remove-orphans --wait --wait-timeout 120
  echo "Previous image restored." >&2
fi
exit 1
