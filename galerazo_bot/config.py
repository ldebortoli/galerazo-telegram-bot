from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    telegram_dev_user_ids: frozenset[str]
    telegram_log_chat_id: str | None
    telegram_announcements_chat_id: str | None
    database_path: Path
    google_sheets_credentials_json_path: Path | None
    google_sheets_spreadsheet_id: str | None
    google_sheets_worksheet_name: str
    openai_api_key: str | None = None
    google_cloud_billing_project_id: str | None = None
    google_cloud_billing_table: str | None = None
    google_cloud_billing_report_time: str = "09:00"
    telegram_hisopo_common_file_id: str | None = None
    telegram_hisopo_silver_file_id: str | None = None
    telegram_hisopo_gold_file_id: str | None = None


def load_settings() -> Settings:
    load_dotenv()

    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_dev_user_ids=_parse_id_list(os.getenv("TELEGRAM_DEV_USER_IDS", "")),
        telegram_log_chat_id=os.getenv("TELEGRAM_LOG_CHAT_ID") or None,
        telegram_announcements_chat_id=os.getenv("TELEGRAM_ANNOUNCEMENTS_CHAT_ID") or None,
        database_path=Path(os.getenv("DATABASE_PATH", "data/galerazo.sqlite3")),
        google_sheets_credentials_json_path=_optional_path(os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON_PATH")),
        google_sheets_spreadsheet_id=os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID") or None,
        google_sheets_worksheet_name=os.getenv("GOOGLE_SHEETS_WORKSHEET_NAME", "Gastos"),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        google_cloud_billing_project_id=os.getenv("GOOGLE_CLOUD_BILLING_PROJECT_ID") or None,
        google_cloud_billing_table=os.getenv("GOOGLE_CLOUD_BILLING_TABLE") or None,
        google_cloud_billing_report_time=os.getenv(
            "GOOGLE_CLOUD_BILLING_REPORT_TIME", "09:00"
        ),
        telegram_hisopo_common_file_id=os.getenv("TELEGRAM_HISOPO_COMMON_FILE_ID") or None,
        telegram_hisopo_silver_file_id=os.getenv("TELEGRAM_HISOPO_SILVER_FILE_ID") or None,
        telegram_hisopo_gold_file_id=os.getenv("TELEGRAM_HISOPO_GOLD_FILE_ID") or None,
    )


def _parse_id_list(raw_value: str) -> frozenset[str]:
    return frozenset(item.strip() for item in raw_value.split(",") if item.strip())


def _optional_path(raw_value: str | None) -> Path | None:
    if not raw_value:
        return None
    return Path(raw_value)
