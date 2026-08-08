from __future__ import annotations

import sqlite3

from ..command_model import Command
from ..database import Database
from ..roles import CommandContext, UserLevel


async def handle(context: CommandContext, _db: Database) -> str | None:
    if context.chat_type not in {"private", "group", "supergroup"}:
        return context.t("config.unsupported_chat")
    if context.chat_type in {"group", "supergroup"} and context.user_level < UserLevel.ADMIN:
        return context.t("permission_denied")

    if context.send_config_menu is None:
        return context.t("config.not_configured")

    if not await context.send_config_menu():
        return context.t("config.send_failed")

    return None


def migrate_chat_data(conn: sqlite3.Connection, old_chat_id: str, new_chat_id: str) -> None:
    conn.execute(
        """
        INSERT INTO chat_settings (chat_id, language, announcements_enabled, created_at, updated_at)
        SELECT ?, language, announcements_enabled, created_at, CURRENT_TIMESTAMP
        FROM chat_settings
        WHERE chat_id = ?
        ON CONFLICT(chat_id) DO UPDATE SET
            language = excluded.language,
            announcements_enabled = excluded.announcements_enabled,
            updated_at = CURRENT_TIMESTAMP
        """,
        (new_chat_id, old_chat_id),
    )
    conn.execute("DELETE FROM chat_settings WHERE chat_id = ?", (old_chat_id,))
    settings = conn.execute(
        "SELECT command_group, enabled FROM chat_command_settings WHERE chat_id = ?",
        (old_chat_id,),
    ).fetchall()
    for setting in settings:
        conn.execute(
            """
            INSERT INTO chat_command_settings (chat_id, command_group, enabled, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(chat_id, command_group) DO UPDATE SET
                enabled = excluded.enabled,
                updated_at = CURRENT_TIMESTAMP
            """,
            (new_chat_id, setting["command_group"], setting["enabled"]),
        )
    conn.execute("DELETE FROM chat_command_settings WHERE chat_id = ?", (old_chat_id,))


COMMANDS = {
    "config": Command("config", "muestra la configuracion del chat", handle),
}
