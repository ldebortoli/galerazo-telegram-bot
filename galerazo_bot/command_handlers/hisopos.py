from __future__ import annotations

import json
import logging
import sqlite3

from telegram import Message
from telegram.error import TelegramError

from ..command_model import Command
from ..database import Database
from ..hisopos import build_hisopo_pages, render_hisopo_page
from ..pagination import bold_first_line_entities, build_keyboard
from ..roles import CommandContext


logger = logging.getLogger(__name__)


async def handle(context: CommandContext, _db: Database) -> str | None:
    if context.chat_type not in {"group", "supergroup"}:
        return context.t("hisopos.group_only")
    if context.send_hisopos is None:
        return context.t("hisopos.not_configured")
    if not await context.send_hisopos():
        return context.t("hisopos.send_failed")
    return None


async def send_hisopos(
    db: Database,
    message: Message,
    requester_user_id: str,
) -> bool:
    language = db.get_chat_settings(str(message.chat.id)).language
    scores = db.get_hisopo_scores(str(message.chat.id))
    page = render_hisopo_page(scores, page=1, language=language)
    content_json = json.dumps({"pages": build_hisopo_pages(scores, language)}, ensure_ascii=False)
    try:
        entities = bold_first_line_entities(page.text)
        result = await message.reply_text(page.text, do_quote=True, entities=entities)
        message_id = str(result.message_id)
        if page.total_pages > 1 and message_id:
            db.save_paginated_message_state(
                chat_id=str(message.chat.id),
                message_id=message_id,
                list_type="hisopos",
                requester_user_id=requester_user_id,
                content_json=content_json,
                unlocked=False,
                current_page=page.page,
            )
            await result.edit_text(
                text=page.text,
                reply_markup=build_keyboard(message_id, page.page, page.total_pages, unlocked=False),
                entities=entities,
            )
        return True
    except TelegramError as exc:
        logger.warning("No pude enviar ranking de Hisopos: %s", exc)
        return False


def migrate_chat_data(conn: sqlite3.Connection, old_chat_id: str, new_chat_id: str) -> None:
    conn.execute(
        """
        INSERT INTO hisopo_chat_settings (
            chat_id, intensity_percent, created_at, updated_at
        )
        SELECT ?, intensity_percent, created_at, CURRENT_TIMESTAMP
        FROM hisopo_chat_settings
        WHERE chat_id = ?
        ON CONFLICT(chat_id) DO UPDATE SET
            intensity_percent = excluded.intensity_percent,
            updated_at = CURRENT_TIMESTAMP
        """,
        (new_chat_id, old_chat_id),
    )
    conn.execute("DELETE FROM hisopo_chat_settings WHERE chat_id = ?", (old_chat_id,))

    scores = conn.execute(
        "SELECT user_id, points FROM hisopo_scores WHERE chat_id = ?",
        (old_chat_id,),
    ).fetchall()
    for score in scores:
        conn.execute(
            """
            INSERT INTO hisopo_scores (chat_id, user_id, points, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                points = hisopo_scores.points + excluded.points,
                updated_at = CURRENT_TIMESTAMP
            """,
            (new_chat_id, score["user_id"], score["points"]),
        )
    conn.execute("DELETE FROM hisopo_scores WHERE chat_id = ?", (old_chat_id,))

    conn.execute(
        """
        INSERT OR IGNORE INTO hisopo_spawns (
            chat_id, message_id, hisopo_type, points, source, spawned_at, expires_at,
            status, winner_user_id, captured_at
        )
        SELECT ?, message_id, hisopo_type, points, source, spawned_at, expires_at,
               status, winner_user_id, captured_at
        FROM hisopo_spawns
        WHERE chat_id = ?
        """,
        (new_chat_id, old_chat_id),
    )
    conn.execute("DELETE FROM hisopo_spawns WHERE chat_id = ?", (old_chat_id,))
    conn.execute(
        "UPDATE hisopo_schedules SET chat_id = ? WHERE chat_id = ?",
        (new_chat_id, old_chat_id),
    )


COMMANDS = {
    "hisopos": Command(
        "hisopos",
        "muestra la tabla del Recolector de Hisopos",
        handle,
        configurable_group="hisopos",
    )
}
