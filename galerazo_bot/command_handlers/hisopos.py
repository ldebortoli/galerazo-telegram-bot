from __future__ import annotations

import json
import logging
import sqlite3

from telegram import Message
from telegram.error import TelegramError

from ..command_model import Command
from ..database import Database
from ..hisopos import build_hisopo_pages, render_hisopo_collection, render_hisopo_page
from ..pagination import bold_first_line_entities, build_keyboard
from ..roles import CommandContext


logger = logging.getLogger(__name__)


def handle_rules(context: CommandContext, _db: Database) -> str:
    return context.t("hisopos.rules")


async def handle(context: CommandContext, _db: Database) -> str | None:
    if context.chat_type not in {"group", "supergroup"}:
        return context.t("hisopos.group_only")
    if context.send_hisopos is None:
        return context.t("hisopos.not_configured")
    if not await context.send_hisopos():
        return context.t("hisopos.send_failed")
    return None


def handle_collection(context: CommandContext, db: Database):
    if context.chat_type not in {"group", "supergroup"} or context.chat_id is None:
        return context.t("hisopos.group_only")
    if context.send_hisopo_collection is not None:
        return _send_collection(context)
    target_user_id = context.reply_to_user_id or context.sender_id
    target_name = (
        context.reply_to_display_name
        or context.reply_to_username
        or context.sender_display_name
        or context.sender_username
        or context.t("user.unknown")
    )
    entries = db.get_hisopo_collection(context.chat_id, target_user_id)
    return render_hisopo_collection(
        entries,
        user_name=target_name,
        user_id=target_user_id,
        language=context.language,
    )


async def _send_collection(context: CommandContext) -> str | None:
    if await context.send_hisopo_collection():
        return None
    return context.t("hisopos.send_failed")


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

    collection = conn.execute(
        """
        SELECT user_id, hisopo_type, capture_count,
               first_captured_at, last_captured_at
        FROM hisopo_collections
        WHERE chat_id = ?
        """,
        (old_chat_id,),
    ).fetchall()
    for entry in collection:
        conn.execute(
            """
            INSERT INTO hisopo_collections (
                chat_id, user_id, hisopo_type, capture_count,
                first_captured_at, last_captured_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(chat_id, user_id, hisopo_type) DO UPDATE SET
                capture_count = hisopo_collections.capture_count + excluded.capture_count,
                first_captured_at = MIN(
                    hisopo_collections.first_captured_at,
                    excluded.first_captured_at
                ),
                last_captured_at = MAX(
                    hisopo_collections.last_captured_at,
                    excluded.last_captured_at
                )
            """,
            (
                new_chat_id,
                entry["user_id"],
                entry["hisopo_type"],
                entry["capture_count"],
                entry["first_captured_at"],
                entry["last_captured_at"],
            ),
        )
    conn.execute("DELETE FROM hisopo_collections WHERE chat_id = ?", (old_chat_id,))

    conn.execute(
        """
        INSERT OR IGNORE INTO hisopo_spawns (
            chat_id, message_id, hisopo_type, appearance_type,
            initial_appearance_type, points, required_helpers, source,
            spawned_at, expires_at, status, winner_user_id, captured_at,
            bomb_success_slot, bomb_explosion_slot, bomb_revealed_mask,
            message_cleanup_status,
            message_cleanup_attempts, message_cleanup_last_attempt_at,
            message_deleted_at, message_cleanup_error
        )
        SELECT ?, message_id, hisopo_type, appearance_type,
               initial_appearance_type, points, required_helpers, source,
               spawned_at, expires_at, status, winner_user_id, captured_at,
               bomb_success_slot, bomb_explosion_slot, bomb_revealed_mask,
               message_cleanup_status,
               message_cleanup_attempts, message_cleanup_last_attempt_at,
               message_deleted_at, message_cleanup_error
        FROM hisopo_spawns
        WHERE chat_id = ?
        """,
        (new_chat_id, old_chat_id),
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO hisopo_giant_contributions (
            chat_id, message_id, user_id, contributed_at
        )
        SELECT ?, contribution.message_id, contribution.user_id,
               contribution.contributed_at
        FROM hisopo_giant_contributions AS contribution
        JOIN hisopo_spawns AS old_spawn
          ON old_spawn.chat_id = contribution.chat_id
         AND old_spawn.message_id = contribution.message_id
        JOIN hisopo_spawns AS new_spawn
          ON new_spawn.chat_id = ?
         AND new_spawn.message_id = old_spawn.message_id
         AND new_spawn.hisopo_type = old_spawn.hisopo_type
         AND new_spawn.spawned_at = old_spawn.spawned_at
        WHERE contribution.chat_id = ?
        """,
        (new_chat_id, new_chat_id, old_chat_id),
    )
    conn.execute(
        "DELETE FROM hisopo_giant_contributions WHERE chat_id = ?",
        (old_chat_id,),
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO hisopo_race_presses (
            chat_id, message_id, callback_query_id,
            user_id, pressed_at, counted
        )
        SELECT ?, press.message_id, press.callback_query_id,
               press.user_id, press.pressed_at, press.counted
        FROM hisopo_race_presses AS press
        JOIN hisopo_spawns AS new_spawn
          ON new_spawn.chat_id = ?
         AND new_spawn.message_id = press.message_id
        WHERE press.chat_id = ?
        """,
        (new_chat_id, new_chat_id, old_chat_id),
    )
    conn.execute(
        "DELETE FROM hisopo_race_presses WHERE chat_id = ?",
        (old_chat_id,),
    )
    conn.execute("DELETE FROM hisopo_spawns WHERE chat_id = ?", (old_chat_id,))
    conn.execute(
        "UPDATE hisopo_schedules SET chat_id = ? WHERE chat_id = ?",
        (new_chat_id, old_chat_id),
    )


COMMANDS = {
    "coleccionhisopos": Command(
        "coleccionhisopos",
        "muestra tu colección histórica de Hisopos",
        handle_collection,
        configurable_group="hisopos",
    ),
    "reglashisopo": Command(
        "reglashisopo",
        "muestra las reglas del Recolector de Hisopos",
        handle_rules,
        response_parse_mode="HTML",
    ),
    "hisopos": Command(
        "hisopos",
        "muestra la tabla del Recolector de Hisopos",
        handle,
        configurable_group="hisopos",
    )
}
