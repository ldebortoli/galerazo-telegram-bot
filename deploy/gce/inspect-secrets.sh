#!/usr/bin/env bash
set -Eeuo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Este script debe ejecutarse como root." >&2
  exit 1
fi

python3 - /etc/galerazo/bot.env /etc/galerazo/secrets/google-service-account.json <<'PY'
import json
from pathlib import Path
import sys

env_path = Path(sys.argv[1])
credentials_path = Path(sys.argv[2])
keys = (
    "TELEGRAM_BOT_TOKEN",
    "OPENAI_API_KEY",
    "TELEGRAM_DEV_USER_IDS",
    "TELEGRAM_LOG_CHAT_ID",
    "TELEGRAM_ANNOUNCEMENTS_CHAT_ID",
    "GOOGLE_SHEETS_SPREADSHEET_ID",
    "GOOGLE_SHEETS_WORKSHEET_NAME",
    "GOOGLE_CLOUD_BILLING_PROJECT_ID",
    "GOOGLE_CLOUD_BILLING_TABLE",
    "GOOGLE_CLOUD_BILLING_REPORT_TIME",
)

values: dict[str, str] = {}
if env_path.is_file():
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        if not raw_line or raw_line.lstrip().startswith("#") or "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        values[key.strip()] = value.strip()

fields = {
    key: bool(values.get(key)) and values.get(key) != "replace-me"
    for key in keys
}
fields["GOOGLE_SHEETS_CREDENTIALS_JSON"] = (
    credentials_path.is_file() and credentials_path.stat().st_size > 0
)
print(json.dumps(fields, separators=(",", ":"), sort_keys=True))
PY
