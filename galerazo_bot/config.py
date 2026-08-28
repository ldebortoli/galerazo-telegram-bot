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
    telegram_owner_user_id: str | None = None
    openai_api_key: str | None = None
    google_cloud_billing_project_id: str | None = None
    google_cloud_billing_table: str | None = None
    google_cloud_billing_report_time: str = "09:00"
    telegram_hisopo_common_file_id: str | None = None
    telegram_hisopo_silver_file_id: str | None = None
    telegram_hisopo_gold_file_id: str | None = None
    telegram_hisopo_diamond_file_id: str | None = None
    telegram_hisopo_fleeting_file_id: str | None = None
    telegram_hisopo_mystery_file_id: str | None = None
    telegram_hisopo_putrid_file_id: str | None = None
    telegram_hisopo_used_file_id: str | None = None
    telegram_hisopo_radioactive_file_id: str | None = None
    telegram_hisopo_bomb_file_id: str | None = None
    telegram_hisopo_bomb_defused_file_id: str | None = None
    telegram_hisopo_bomb_exploded_file_id: str | None = None
    telegram_hisopo_frenetic_file_id: str | None = None
    telegram_hisopo_black_hole_file_id: str | None = None
    telegram_hisopo_expired_file_id: str | None = None
    telegram_hisopo_fake_file_id: str | None = None
    telegram_hisopo_twin_file_id: str | None = None
    telegram_hisopo_giant_file_id: str | None = None
    telegram_hisopo_miracle_file_id: str | None = None
    telegram_mini_app_url: str | None = None
    telegram_mini_app_short_name: str = "hisopos"
    mini_app_bind_host: str = "127.0.0.1"
    mini_app_port: int = 8080
    telegram_expense_user_ids: frozenset[str] = frozenset()
    google_sheets_cashflow_sheet_prefix: str = "Gastos"


def load_settings() -> Settings:
    load_dotenv()

    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_dev_user_ids=_parse_id_list(os.getenv("TELEGRAM_DEV_USER_IDS", "")),
        telegram_expense_user_ids=_parse_id_list(os.getenv("TELEGRAM_EXPENSE_USER_IDS", "")),
        telegram_owner_user_id=os.getenv("TELEGRAM_OWNER_USER_ID") or None,
        telegram_log_chat_id=os.getenv("TELEGRAM_LOG_CHAT_ID") or None,
        telegram_announcements_chat_id=os.getenv("TELEGRAM_ANNOUNCEMENTS_CHAT_ID") or None,
        database_path=Path(os.getenv("DATABASE_PATH", "data/galerazo.sqlite3")),
        google_sheets_credentials_json_path=_optional_path(os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON_PATH")),
        google_sheets_spreadsheet_id=os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID") or None,
        google_sheets_worksheet_name=os.getenv("GOOGLE_SHEETS_WORKSHEET_NAME", "Gastos y compras"),
        google_sheets_cashflow_sheet_prefix=os.getenv(
            "GOOGLE_SHEETS_CASHFLOW_SHEET_PREFIX", "Gastos"
        ),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        google_cloud_billing_project_id=os.getenv("GOOGLE_CLOUD_BILLING_PROJECT_ID") or None,
        google_cloud_billing_table=os.getenv("GOOGLE_CLOUD_BILLING_TABLE") or None,
        google_cloud_billing_report_time=os.getenv(
            "GOOGLE_CLOUD_BILLING_REPORT_TIME", "09:00"
        ),
        telegram_hisopo_common_file_id=os.getenv("TELEGRAM_HISOPO_COMMON_FILE_ID") or None,
        telegram_hisopo_silver_file_id=os.getenv("TELEGRAM_HISOPO_SILVER_FILE_ID") or None,
        telegram_hisopo_gold_file_id=os.getenv("TELEGRAM_HISOPO_GOLD_FILE_ID") or None,
        telegram_hisopo_diamond_file_id=os.getenv("TELEGRAM_HISOPO_DIAMOND_FILE_ID") or None,
        telegram_hisopo_fleeting_file_id=os.getenv("TELEGRAM_HISOPO_FLEETING_FILE_ID") or None,
        telegram_hisopo_mystery_file_id=os.getenv("TELEGRAM_HISOPO_MYSTERY_FILE_ID") or None,
        telegram_hisopo_putrid_file_id=os.getenv("TELEGRAM_HISOPO_PUTRID_FILE_ID") or None,
        telegram_hisopo_used_file_id=os.getenv("TELEGRAM_HISOPO_USED_FILE_ID") or None,
        telegram_hisopo_radioactive_file_id=os.getenv("TELEGRAM_HISOPO_RADIOACTIVE_FILE_ID") or None,
        telegram_hisopo_bomb_file_id=os.getenv("TELEGRAM_HISOPO_BOMB_FILE_ID") or None,
        telegram_hisopo_bomb_defused_file_id=os.getenv(
            "TELEGRAM_HISOPO_BOMB_DEFUSED_FILE_ID"
        )
        or None,
        telegram_hisopo_bomb_exploded_file_id=os.getenv(
            "TELEGRAM_HISOPO_BOMB_EXPLODED_FILE_ID"
        )
        or None,
        telegram_hisopo_frenetic_file_id=os.getenv("TELEGRAM_HISOPO_FRENETIC_FILE_ID")
        or None,
        telegram_hisopo_black_hole_file_id=os.getenv(
            "TELEGRAM_HISOPO_BLACK_HOLE_FILE_ID"
        )
        or None,
        telegram_hisopo_expired_file_id=os.getenv("TELEGRAM_HISOPO_EXPIRED_FILE_ID")
        or None,
        telegram_hisopo_fake_file_id=os.getenv("TELEGRAM_HISOPO_FAKE_FILE_ID") or None,
        telegram_hisopo_twin_file_id=os.getenv("TELEGRAM_HISOPO_TWIN_FILE_ID") or None,
        telegram_hisopo_giant_file_id=os.getenv("TELEGRAM_HISOPO_GIANT_FILE_ID") or None,
        telegram_hisopo_miracle_file_id=os.getenv("TELEGRAM_HISOPO_MIRACLE_FILE_ID") or None,
        telegram_mini_app_url=os.getenv("TELEGRAM_MINI_APP_URL") or None,
        telegram_mini_app_short_name=os.getenv("TELEGRAM_MINI_APP_SHORT_NAME", "hisopos"),
        mini_app_bind_host=os.getenv("MINI_APP_BIND_HOST", "127.0.0.1"),
        mini_app_port=int(os.getenv("MINI_APP_PORT", "8080")),
    )


def _parse_id_list(raw_value: str) -> frozenset[str]:
    return frozenset(item.strip() for item in raw_value.split(",") if item.strip())


def _optional_path(raw_value: str | None) -> Path | None:
    if not raw_value:
        return None
    return Path(raw_value)
