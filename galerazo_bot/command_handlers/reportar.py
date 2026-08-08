from __future__ import annotations

import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from ..command_model import Command
from ..database import Database
from ..roles import CommandContext


async def handle(context: CommandContext, db: Database) -> str:
    report = context.args.strip()
    if not report:
        return context.t("reportar.usage")

    if context.send_report is None:
        return context.t("reportar.not_configured")

    if not db.try_record_daily_report(context.sender_id, _today_key(), context.chat_id):
        return context.t("reportar.rate_limited")

    if not await context.send_report(report):
        return context.t("reportar.send_failed")

    return context.t("reportar.sent")


def _today_key() -> str:
    try:
        now = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))
    except Exception:
        now = datetime.now().astimezone()
    return now.date().isoformat()


def migrate_chat_data(conn: sqlite3.Connection, old_chat_id: str, new_chat_id: str) -> None:
    conn.execute("UPDATE daily_user_reports SET chat_id = ? WHERE chat_id = ?", (new_chat_id, old_chat_id))


COMMANDS = {
    "reportar": Command("reportar", "reporta un bug al canal de logging", handle),
}
