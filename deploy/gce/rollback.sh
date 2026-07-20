#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script with sudo." >&2
  exit 1
fi

app_dir=/opt/galerazo
compose_file="${app_dir}/compose.yaml"
image_env="${app_dir}/image.env"
previous_env="${app_dir}/previous-image.env"

if [[ ! -f "${previous_env}" ]]; then
  echo "There is no previous image recorded." >&2
  exit 1
fi

current_image="$(sed -n 's/^GALERAZO_IMAGE=//p' "${image_env}" | head -n 1)"
previous_image="$(sed -n 's/^GALERAZO_IMAGE=//p' "${previous_env}" | head -n 1)"
if [[ -z "${previous_image}" ]]; then
  echo "The previous image reference is empty." >&2
  exit 1
fi

temporary_env="$(mktemp "${app_dir}/image.env.XXXXXX")"
trap 'rm -f "${temporary_env}"' EXIT
printf 'GALERAZO_IMAGE=%s\n' "${current_image}" > "${temporary_env}"
cp "${previous_env}" "${image_env}"
chmod 0600 "${image_env}"

if docker compose --env-file "${image_env}" -f "${compose_file}" \
    up -d --remove-orphans --wait --wait-timeout 120; then
  cp "${temporary_env}" "${previous_env}"
  chmod 0600 "${previous_env}"
  docker compose --env-file "${image_env}" -f "${compose_file}" ps
  echo "Rollback completed: ${previous_image}"
  exit 0
fi

echo "Rollback failed; restoring the current image reference." >&2
cp "${temporary_env}" "${image_env}"
chmod 0600 "${image_env}"
docker compose --env-file "${image_env}" -f "${compose_file}" up -d --remove-orphans
exit 1
