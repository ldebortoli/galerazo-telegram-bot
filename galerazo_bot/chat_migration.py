from __future__ import annotations

import sqlite3

from telegram import Message

from . import pagination
from .command_handlers import config, galerazas, gastos, reiniciarbot, reportar, restrictions, ruletarusa, triggers


def chat_migration_ids(message: Message) -> tuple[int, int] | None:
    """Return the canonical old and new IDs for either Telegram migration update."""
    if message.chat is None:
        return None
    if message.migrate_to_chat_id is not None:
        return message.chat.id, message.migrate_to_chat_id
    if message.migrate_from_chat_id is not None:
        return message.migrate_from_chat_id, message.chat.id
    return None


def migrate_command_data(conn: sqlite3.Connection, old_chat_id: str, new_chat_id: str) -> None:
    """Move command-owned rows as part of Database.migrate_chat_id's transaction."""
    for migrate_data in (
        config.migrate_chat_data,
        reportar.migrate_chat_data,
        restrictions.migrate_chat_data,
        galerazas.migrate_chat_data,
        pagination.migrate_chat_data,
        reiniciarbot.migrate_chat_data,
        gastos.migrate_chat_data,
        triggers.migrate_chat_data,
        ruletarusa.migrate_chat_data,
    ):
        migrate_data(conn, old_chat_id, new_chat_id)
