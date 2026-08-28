#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script with sudo." >&2
  exit 1
fi

source /etc/os-release
case "${ID}" in
  ubuntu|debian) ;;
  *)
    echo "Unsupported operating system: ${ID}. Use Ubuntu or Debian." >&2
    exit 1
    ;;
esac

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl gnupg

install -m 0755 -d /etc/apt/keyrings
curl -fsSL "https://download.docker.com/linux/${ID}/gpg" -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/${ID}
Suites: ${VERSION_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
  | gpg --dearmor --yes -o /etc/apt/keyrings/cloud.google.gpg
cat > /etc/apt/sources.list.d/google-cloud-sdk.sources <<EOF
Types: deb
URIs: https://packages.cloud.google.com/apt
Suites: cloud-sdk
Components: main
Signed-By: /etc/apt/keyrings/cloud.google.gpg
EOF

apt-get update
apt-get install -y \
  containerd.io \
  docker-buildx-plugin \
  docker-ce \
  docker-ce-cli \
  docker-compose-plugin \
  google-cloud-cli

systemctl enable --now docker

install -d -m 0755 /opt/galerazo
install -d -m 0755 -o 10001 -g 10001 /srv/galerazo/data
install -d -m 0755 -o 10001 -g 10001 /srv/galerazo/backups
install -d -m 0700 /etc/galerazo
install -d -m 0700 /etc/galerazo/secrets

if [[ ! -f /etc/galerazo/bot.env ]]; then
  cat > /etc/galerazo/bot.env <<'EOF'
TELEGRAM_BOT_TOKEN=replace-me
OPENAI_API_KEY=
TELEGRAM_DEV_USER_IDS=
TELEGRAM_OWNER_USER_ID=
TELEGRAM_LOG_CHAT_ID=
TELEGRAM_ANNOUNCEMENTS_CHAT_ID=
TELEGRAM_HISOPO_COMMON_FILE_ID=
TELEGRAM_HISOPO_SILVER_FILE_ID=
TELEGRAM_HISOPO_GOLD_FILE_ID=
TELEGRAM_HISOPO_DIAMOND_FILE_ID=
TELEGRAM_HISOPO_FLEETING_FILE_ID=
TELEGRAM_HISOPO_MYSTERY_FILE_ID=
TELEGRAM_HISOPO_PUTRID_FILE_ID=
TELEGRAM_HISOPO_RADIOACTIVE_FILE_ID=
TELEGRAM_HISOPO_BOMB_FILE_ID=
TELEGRAM_HISOPO_BOMB_DEFUSED_FILE_ID=
TELEGRAM_HISOPO_BOMB_EXPLODED_FILE_ID=
TELEGRAM_HISOPO_FRENETIC_FILE_ID=
TELEGRAM_HISOPO_BLACK_HOLE_FILE_ID=
TELEGRAM_HISOPO_EXPIRED_FILE_ID=
TELEGRAM_HISOPO_FAKE_FILE_ID=
TELEGRAM_HISOPO_TWIN_FILE_ID=
TELEGRAM_HISOPO_GIANT_FILE_ID=
TELEGRAM_HISOPO_MIRACLE_FILE_ID=
TELEGRAM_MINI_APP_URL=
TELEGRAM_MINI_APP_SHORT_NAME=hisopos
MINI_APP_BIND_HOST=0.0.0.0
MINI_APP_PORT=8080
DATABASE_PATH=/app/data/galerazo.sqlite3
GOOGLE_SHEETS_CREDENTIALS_JSON_PATH=
GOOGLE_SHEETS_SPREADSHEET_ID=
GOOGLE_SHEETS_WORKSHEET_NAME=Gastos
GOOGLE_CLOUD_BILLING_PROJECT_ID=
GOOGLE_CLOUD_BILLING_TABLE=
GOOGLE_CLOUD_BILLING_REPORT_TIME=09:00
EOF
  chmod 0600 /etc/galerazo/bot.env
fi

echo
echo "GCE host is ready."
echo "1. Edit /etc/galerazo/bot.env with: sudo nano /etc/galerazo/bot.env"
echo "2. Grant the VM service account Artifact Registry Reader."
echo "3. Publish an image and run Deploy-Gce.ps1 from your workstation."
