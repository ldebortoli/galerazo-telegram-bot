from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from telegram import Message, Update, User
from telegram.error import TelegramError

from ..commands import Command
from ..database import Database
from ..galeraza import build_galeraza_pages, render_galeraza_page
from ..i18n import t
from ..pagination import bold_first_line_entities, build_keyboard
from ..roles import CommandContext


logger = logging.getLogger(__name__)
ARGENTINA_TIMEZONE = ZoneInfo("America/Argentina/Buenos_Aires")


async def handle(context: CommandContext, _db: Database) -> str | None:
    if context.chat_type not in {"group", "supergroup"}:
        return context.t("galeraza.group_only")

    if context.send_galerazas is None:
        return context.t("galeraza.not_configured")

    if not await context.send_galerazas():
        return context.t("galeraza.send_failed")

    return None


def is_galeraza_candidate(update: Update, message: Message, user: User) -> bool:
    return not user.is_bot and update.message is message


def telegram_message_datetime(message: Message) -> datetime:
    message_date = message.date
    if message_date.tzinfo is None:
        return message_date.replace(tzinfo=timezone.utc)
    return message_date


def galeraza_game_date(message: Message) -> str:
    return telegram_message_datetime(message).astimezone(ARGENTINA_TIMEZONE).date().isoformat()


async def maybe_award_daily_galeraza(
    db: Database,
    message: Message,
    user_id: str,
) -> None:
    if message.chat.type not in {"group", "supergroup"}:
        return
    if not db.is_command_group_enabled(str(message.chat.id), "galeraza"):
        return

    message_date = telegram_message_datetime(message)
    awarded = db.try_award_daily_galeraza(
        chat_id=str(message.chat.id),
        game_date=galeraza_game_date(message),
        user_id=user_id,
        message_id=str(message.message_id),
        message_date=message_date.isoformat(),
    )
    if awarded:
        await message.reply_text(t(_language(db, message.chat.id), "galeraza.win"), do_quote=True)


async def send_galerazas(
    db: Database,
    message: Message,
    requester_user_id: str,
) -> bool:
    language = _language(db, message.chat.id)
    scores = db.get_galeraza_scores(str(message.chat.id))
    page = render_galeraza_page(scores, page=1, language=language)
    content_json = json.dumps({"pages": build_galeraza_pages(scores, language)}, ensure_ascii=False)
    try:
        entities = bold_first_line_entities(page.text)
        result = await message.reply_text(page.text, do_quote=True, entities=entities)
        message_id = str(result.message_id)
        if page.total_pages > 1 and message_id:
            db.save_paginated_message_state(
                chat_id=str(message.chat.id),
                message_id=message_id,
                list_type="galeraza",
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
        logger.warning("No pude enviar ranking de Galeraza: %s", exc)
        return False


def _language(db: Database, chat_id: int) -> str:
    return db.get_chat_settings(str(chat_id)).language


COMMANDS = {
    "galerazas": Command(
        "galerazas",
        "muestra el ranking de la Galeraza",
        handle,
        configurable_group="galeraza",
    ),
    "galeraza": Command(
        "galeraza",
        "muestra el ranking de la Galeraza",
        handle,
        command_key="galerazas",
        configurable_group="galeraza",
    ),
}
