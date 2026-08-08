from __future__ import annotations

import sqlite3

from ..command_model import Command
from ..database import Database
from ..roles import CommandContext, UserLevel


async def handle(context: CommandContext, _db: Database) -> str | None:
    if context.create_restart_confirmation is None:
        return context.t("restart.not_configured")
    if not await context.create_restart_confirmation():
        return context.t("restart.send_failed")
    return None


def migrate_chat_data(conn: sqlite3.Connection, old_chat_id: str, new_chat_id: str) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO restart_confirmations (
            chat_id, message_id, requester_user_id, created_at
        )
        SELECT ?, message_id, requester_user_id, created_at
        FROM restart_confirmations
        WHERE chat_id = ?
        """,
        (new_chat_id, old_chat_id),
    )
    conn.execute("DELETE FROM restart_confirmations WHERE chat_id = ?", (old_chat_id,))


COMMANDS = {
    "reiniciarbot": Command("reiniciarbot", "solicita reiniciar el bot", handle, UserLevel.DEV),
}
