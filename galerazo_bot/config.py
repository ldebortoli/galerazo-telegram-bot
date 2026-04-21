from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> None:
        return None


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    telegram_dev_user_ids: frozenset[str]
    telegram_log_chat_id: str | None
    telegram_announcements_chat_id: str | None
    database_path: Path


def load_settings() -> Settings:
    load_dotenv()

    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_dev_user_ids=_parse_id_list(os.getenv("TELEGRAM_DEV_USER_IDS", "")),
        telegram_log_chat_id=os.getenv("TELEGRAM_LOG_CHAT_ID") or None,
        telegram_announcements_chat_id=os.getenv("TELEGRAM_ANNOUNCEMENTS_CHAT_ID") or None,
        database_path=Path(os.getenv("DATABASE_PATH", "data/galerazo.sqlite3")),
    )


def _parse_id_list(raw_value: str) -> frozenset[str]:
    return frozenset(item.strip() for item in raw_value.split(",") if item.strip())
