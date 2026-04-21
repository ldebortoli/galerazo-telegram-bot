from __future__ import annotations

import json
import logging
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram import Bot, Chat, ChatMember, Message, Update, User
from telegram.error import BadRequest, Forbidden, TelegramError
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackContext,
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .chat_config import (
    CONFIG_PREFIX,
    build_command_group_menu,
    build_command_groups_menu,
    build_language_menu,
    build_main_menu,
    command_group_label,
    is_valid_command_group,
    is_valid_language,
    parse_config_callback,
)
from .commands import COMMANDS, command_exists, get_command, handle_command_async, is_command_invocation
from .config import Settings, load_settings
from .database import Database
from .galeraza import build_galeraza_lines, render_galeraza_page
from .i18n import DEFAULT_LANGUAGE, t
from .pagination import BUTTON_PREFIX, build_keyboard, parse_callback_data, render_page
from .roles import BackupResult, UserLevel


logger = logging.getLogger(__name__)
TELEGRAM_DOCUMENT_UPLOAD_LIMIT_BYTES = 50 * 1024 * 1024
TELEGRAM_MESSAGE_LIMIT_CHARS = 4096
PAGINATED_METADATA_TTL = timedelta(days=14)


@dataclass(frozen=True)
class BotState:
    db: Database
    settings: Settings
    bot_user_id: str


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    settings = load_settings()
    if not settings.telegram_bot_token:
        raise RuntimeError("Falta TELEGRAM_BOT_TOKEN en el archivo .env")

    db = Database(settings.database_path)
    application = (
        ApplicationBuilder()
        .token(settings.telegram_bot_token)
        .post_init(_post_init)
        .concurrent_updates(False)
        .build()
    )
    application.bot_data["settings"] = settings
    application.bot_data["db"] = db

    _register_handlers(application)
    application.add_error_handler(_handle_error)

    logger.info("Galerazo Bot escuchando mensajes de Telegram.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


def _register_handlers(application: Application) -> None:
    application.add_handler(MessageHandler(filters.ALL, _preprocess_message), group=0)

    for command_name in COMMANDS:
        application.add_handler(CommandHandler(command_name, _command_entrypoint), group=1)

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _text_command_entrypoint), group=1)
    application.add_handler(CallbackQueryHandler(_callback_query_entrypoint, pattern=f"^{BUTTON_PREFIX}:"), group=1)
    application.add_handler(CallbackQueryHandler(_config_callback_entrypoint, pattern=f"^{CONFIG_PREFIX}:"), group=1)
    application.add_handler(ChatMemberHandler(_my_chat_member_entrypoint, ChatMemberHandler.MY_CHAT_MEMBER), group=1)
    application.add_handler(MessageHandler(filters.COMMAND, _unknown_command_entrypoint), group=2)


async def _post_init(application: Application) -> None:
    settings = application.bot_data["settings"]
    db = application.bot_data["db"]
    bot_user = await application.bot.get_me()
    application.bot_data["state"] = BotState(
        db=db,
        settings=settings,
        bot_user_id=str(bot_user.id),
    )

    await _cleanup_old_paginated_messages(db, application.bot)
    await _send_log_event(application.bot, settings.telegram_log_chat_id, "Galerazo Bot iniciado.")


def _state(context: CallbackContext) -> BotState:
    return context.application.bot_data["state"]


async def _preprocess_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    message = update.effective_message
    if message is None:
        return

    if _handle_chat_migration(message, state.db):
        return

    _register_chat_from_message(message, state.db)
    _register_bot_added_event(message, state.db, state.bot_user_id)
    _register_bot_removed_event(message, state.db, state.bot_user_id)

    user = update.effective_user
    chat = update.effective_chat
    if user is None or chat is None:
        return

    state.db.get_or_create_user(str(user.id), _display_name(user), user.username)
    if state.db.is_user_blocked(str(user.id)):
        return

    await _maybe_award_daily_galeraza(
        db=state.db,
        message=message,
        user_id=str(user.id),
    )

    text = message.text
    if not text or is_command_invocation(text):
        return

    state.db.save_incoming_message(sender_id=str(user.id), text=text, chat_id=str(chat.id))


async def _command_entrypoint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _handle_command_update(update, context)


async def _text_command_entrypoint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None or not message.text:
        return

    if not is_command_invocation(message.text):
        return

    await _handle_command_update(update, context)


async def _unknown_command_entrypoint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    message = update.effective_message
    if message is None:
        return
    await message.reply_text(t(_chat_language(state.db, message.chat.id), "unknown_command"))


async def _handle_command_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if message is None or user is None or chat is None or not message.text:
        return

    state.db.get_or_create_user(str(user.id), _display_name(user), user.username)
    if state.db.is_user_blocked(str(user.id)):
        return

    user_level = UserLevel.COMMON
    command = get_command(message.text)
    if command is not None and _is_command_group_disabled(state.db, chat, command.configurable_group):
        return

    if command_exists(message.text):
        user_level = await _resolve_user_level(
            user_id=str(user.id),
            chat=chat,
            db=state.db,
            bot=context.bot,
            dev_user_ids=state.settings.telegram_dev_user_ids,
        )

    reply_to_user = message.reply_to_message.from_user if message.reply_to_message else None
    response = await handle_command_async(
        text=message.text,
        sender_id=str(user.id),
        db=state.db,
        chat_id=str(chat.id),
        user_level=user_level,
        sender_username=user.username,
        sender_display_name=_display_name(user),
        reply_to_user_id=str(reply_to_user.id) if reply_to_user is not None else None,
        reply_to_username=reply_to_user.username if reply_to_user is not None else None,
        reply_to_display_name=_display_name(reply_to_user) if reply_to_user is not None else None,
        chat_type=chat.type,
        language=_chat_language(state.db, chat.id),
        bot_user_id=state.bot_user_id,
        send_announcement=lambda text: _send_announcement(
            context.bot,
            state.settings.telegram_announcements_chat_id,
            text,
            state.settings.telegram_log_chat_id,
            _chat_language(state.db, chat.id),
        ),
        send_report=lambda text: _send_report(
            db=state.db,
            bot=context.bot,
            log_chat_id=state.settings.telegram_log_chat_id,
            message=message,
            user=user,
            report_text=text,
        ),
        create_backup=lambda: _create_and_send_backup(state.db, message),
        send_debug_update=lambda: _send_debug_update(state.db, message, update),
        send_galerazas=lambda: _send_galerazas(state.db, message, str(user.id)),
        send_config_menu=lambda: _send_config_menu(state.db, message),
        leave_chat=lambda: _leave_chat(state.db, context.bot, chat.id),
    )
    if response is None:
        return

    try:
        await _send_text_response(
            db=state.db,
            message=message,
            text=response,
            requester_user_id=str(user.id),
            list_type="command",
            paginate=command.list_response if command is not None else False,
            bot=context.bot,
            log_chat_id=state.settings.telegram_log_chat_id,
        )
    except TelegramError as exc:
        if _is_bot_removed_error(exc):
            state.db.mark_chat_inactive(str(chat.id), "send_message_failed")
            return
        raise


async def _callback_query_entrypoint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    callback_query = update.callback_query
    user = update.effective_user
    if callback_query is None or user is None:
        return

    state.db.get_or_create_user(str(user.id), _display_name(user), user.username)
    if state.db.is_user_blocked(str(user.id)):
        await callback_query.answer()
        return

    parsed = parse_callback_data(callback_query.data or "")
    popup_text = None
    if parsed is not None:
        popup_text = await _handle_paginated_callback(
            callback_query=callback_query,
            db=state.db,
            dev_user_ids=state.settings.telegram_dev_user_ids,
            parsed=parsed,
        )
    await callback_query.answer(text=popup_text)


async def _config_callback_entrypoint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    callback_query = update.callback_query
    user = update.effective_user
    if callback_query is None or user is None:
        return

    state.db.get_or_create_user(str(user.id), _display_name(user), user.username)
    if state.db.is_user_blocked(str(user.id)):
        await callback_query.answer()
        return

    message = callback_query.message
    language = _chat_language(state.db, message.chat.id) if message is not None else DEFAULT_LANGUAGE
    if message is None or message.chat.type not in {"group", "supergroup"}:
        await callback_query.answer(t(language, "config.group_only_popup"))
        return

    user_level = await _resolve_user_level(
        user_id=str(user.id),
        chat=message.chat,
        db=state.db,
        bot=context.bot,
        dev_user_ids=state.settings.telegram_dev_user_ids,
    )
    if user_level < UserLevel.ADMIN:
        await callback_query.answer(t(language, "config.permission_popup"))
        return

    parsed = parse_config_callback(callback_query.data or "")
    if parsed is None:
        await callback_query.answer()
        return

    popup_text = await _handle_config_callback(state.db, message, parsed)
    await callback_query.answer(text=popup_text)


async def _my_chat_member_entrypoint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    chat_member_update = update.my_chat_member
    if chat_member_update is None:
        return

    chat = chat_member_update.chat
    new_chat_member = chat_member_update.new_chat_member
    from_user = chat_member_update.from_user
    user = new_chat_member.user

    if str(user.id) != state.bot_user_id:
        return

    state.db.register_chat(
        chat_id=str(chat.id),
        chat_type=chat.type,
        title=chat.title,
        added_by_user_id=str(from_user.id) if from_user is not None else None,
    )

    if new_chat_member.status in {ChatMember.LEFT, ChatMember.BANNED}:
        state.db.mark_chat_inactive(str(chat.id), new_chat_member.status)


async def _handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Error no handleado procesando update.", exc_info=context.error)
    settings = context.application.bot_data.get("settings")
    if settings is None or context.error is None:
        return
    await _send_unhandled_error_event(context.bot, settings.telegram_log_chat_id, context.error)


def _display_name(user: User | None) -> str | None:
    if user is None:
        return None
    return user.full_name or user.username


async def _maybe_award_daily_galeraza(
    db: Database,
    message: Message,
    user_id: str,
) -> None:
    if message.chat.type not in {"group", "supergroup"}:
        return
    if not db.is_command_group_enabled(str(message.chat.id), "galeraza"):
        return

    game_date = _today_key()
    awarded = db.try_award_daily_galeraza(
        chat_id=str(message.chat.id),
        game_date=game_date,
        user_id=user_id,
        message_id=str(message.message_id),
    )
    if not awarded:
        return

    await message.reply_text(t(_chat_language(db, message.chat.id), "galeraza.win"), do_quote=True)


async def _send_galerazas(
    db: Database,
    message: Message,
    requester_user_id: str,
) -> bool:
    language = _chat_language(db, message.chat.id)
    scores = db.get_galeraza_scores(str(message.chat.id))
    lines = build_galeraza_lines(scores)
    page = render_galeraza_page(scores, page=1, language=language)
    content_json = json.dumps({"header": t(language, "galeraza.header"), "lines": lines}, ensure_ascii=False)
    try:
        result = await message.reply_text(page.text, do_quote=True)
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
            )
        return True
    except TelegramError as exc:
        logger.warning("No pude enviar ranking de Galeraza: %s", exc)
        return False


async def _send_text_response(
    db: Database,
    message: Message,
    text: str,
    requester_user_id: str,
    list_type: str,
    paginate: bool,
    bot: Bot,
    log_chat_id: str | None,
) -> None:
    if len(text) > TELEGRAM_MESSAGE_LIMIT_CHARS and not paginate:
        await message.reply_text(text[:TELEGRAM_MESSAGE_LIMIT_CHARS], do_quote=True)
        await _send_log_event(
            bot,
            log_chat_id,
            (
                f"{t(_chat_language(db, message.chat.id), 'long_message.truncated_log')}\n"
                f"chat_id={message.chat.id} message_id={message.message_id}"
            ),
        )
        return

    lines = text.splitlines()
    header = lines[0] if lines else ""
    body_lines = lines[1:]
    page = render_page(header, body_lines, page=1)

    result = await message.reply_text(page.text, do_quote=True)
    message_id = str(result.message_id)
    if page.total_pages <= 1 or not message_id:
        return

    content_json = json.dumps({"header": header, "lines": body_lines}, ensure_ascii=False)
    db.save_paginated_message_state(
        chat_id=str(message.chat.id),
        message_id=message_id,
        list_type=list_type,
        requester_user_id=requester_user_id,
        content_json=content_json,
        unlocked=False,
        current_page=page.page,
    )
    await result.edit_text(
        text=page.text,
        reply_markup=build_keyboard(message_id, page.page, page.total_pages, unlocked=False),
    )


async def _send_report(
    db: Database,
    bot: Bot,
    log_chat_id: str | None,
    message: Message,
    user: User,
    report_text: str,
) -> bool:
    if not log_chat_id:
        return False

    language = _chat_language(db, message.chat.id)
    username = f"@{user.username}" if user.username else "-"
    display_name = _display_name(user) or "-"
    chat_title = message.chat.title or "-"
    log_text = (
        f"{t(language, 'reportar.log_title')}\n"
        f"user_id={user.id}\n"
        f"username={username}\n"
        f"display_name={display_name}\n"
        f"chat_id={message.chat.id}\n"
        f"chat_type={message.chat.type}\n"
        f"chat_title={chat_title}\n"
        f"message_id={message.message_id}\n"
        "\n"
        f"{report_text}"
    )
    return await _send_log_text_with_truncation(
        bot,
        log_chat_id,
        log_text,
        t(language, "long_message.truncated_log"),
    )


async def _send_config_menu(db: Database, message: Message) -> bool:
    language = _chat_language(db, message.chat.id)
    try:
        await message.reply_text(
            t(language, "config.title"),
            reply_markup=build_main_menu(language),
            do_quote=True,
        )
        db.get_chat_settings(str(message.chat.id))
        return True
    except TelegramError as exc:
        logger.warning("No pude enviar configuracion del chat %s: %s", message.chat.id, exc)
        return False


async def _handle_config_callback(db: Database, message: Message, parsed: tuple[str, ...]) -> str | None:
    action = parsed[0]
    chat_id = str(message.chat.id)
    language = _chat_language(db, message.chat.id)

    if action == "main":
        await message.edit_text(t(language, "config.title"), reply_markup=build_main_menu(language))
        return None

    if action == "language":
        settings = db.get_chat_settings(chat_id)
        await message.edit_text(t(settings.language, "config.language"), reply_markup=build_language_menu(settings.language))
        return None

    if action == "lang" and len(parsed) == 2:
        language = parsed[1]
        if not is_valid_language(language):
            return None
        settings = db.get_chat_settings(chat_id)
        if settings.language == language:
            return None
        db.set_chat_language(chat_id, language)
        await message.edit_text(t(language, "config.language"), reply_markup=build_language_menu(language))
        return t(language, "config.language_updated")

    if action == "commands":
        await message.edit_text(t(language, "config.commands"), reply_markup=build_command_groups_menu(language))
        return None

    if action == "command" and len(parsed) == 2:
        command_group = parsed[1]
        if not is_valid_command_group(command_group):
            return None
        enabled = db.is_command_group_enabled(chat_id, command_group)
        await message.edit_text(
            f"{command_group_label(command_group, language)}\n\n{t(language, 'config.enabled_question')}",
            reply_markup=build_command_group_menu(command_group, enabled, language),
        )
        return None

    if action == "set" and len(parsed) == 3:
        command_group = parsed[1]
        if not is_valid_command_group(command_group):
            return None
        enabled = parsed[2] == "1"
        current_enabled = db.is_command_group_enabled(chat_id, command_group)
        if current_enabled == enabled:
            return None
        db.set_command_group_enabled(chat_id, command_group, enabled)
        await message.edit_text(
            f"{command_group_label(command_group, language)}\n\n{t(language, 'config.enabled_question')}",
            reply_markup=build_command_group_menu(command_group, enabled, language),
        )
        return t(language, "config.updated")

    return None


async def _handle_paginated_callback(
    callback_query,
    db: Database,
    dev_user_ids: frozenset[str],
    parsed: tuple[str, str, str | None],
) -> str | None:
    action, message_id, value = parsed
    user = callback_query.from_user
    message = callback_query.message
    if message is None or message.chat is None:
        return None

    chat_id = message.chat.id
    language = _chat_language(db, chat_id)
    state = db.get_paginated_message_state(str(chat_id), message_id)
    if state is None:
        await _delete_paginated_message(db, message, message_id)
        return t(language, "pagination.deleted")

    if _is_paginated_state_expired(state.created_at):
        await _delete_paginated_message(db, message, message_id)
        return t(language, "pagination.deleted")

    user_id = str(user.id)
    is_dev = user_id in dev_user_ids
    is_owner = user_id == state.requester_user_id
    can_page = state.unlocked or is_owner or is_dev
    can_delete = is_owner or is_dev

    if action == "unlock":
        if not is_owner:
            return None
        unlocked = not state.unlocked
        db.set_paginated_message_unlocked(str(chat_id), message_id, unlocked)
        await _edit_paginated_message(db, message, message_id, page=state.current_page, unlocked=unlocked)
        if unlocked:
            return t(language, "pagination.unlocked")
        return t(language, "pagination.locked")

    if action == "delete":
        if not can_delete:
            return None
        await _delete_paginated_message(db, message, message_id)
        return t(language, "pagination.deleted")

    if action == "page":
        if not can_page or value is None:
            return None
        try:
            target_page = int(value)
        except ValueError:
            return None
        if target_page == state.current_page:
            return None
        await _edit_paginated_message(db, message, message_id, page=target_page, unlocked=state.unlocked)

    return None


async def _delete_paginated_message(
    db: Database,
    message: Message,
    message_id: str,
) -> None:
    try:
        await message.delete()
    except TelegramError as exc:
        logger.warning("No pude eliminar mensaje paginado %s en chat %s: %s", message_id, message.chat.id, exc)
    finally:
        db.delete_paginated_message_state(str(message.chat.id), message_id)


async def _delete_paginated_message_by_id(
    db: Database,
    bot: Bot,
    chat_id: int | str,
    message_id: str,
) -> None:
    try:
        await bot.delete_message(chat_id=chat_id, message_id=int(message_id))
    except TelegramError as exc:
        logger.warning("No pude eliminar mensaje paginado %s en chat %s: %s", message_id, chat_id, exc)
    finally:
        db.delete_paginated_message_state(str(chat_id), message_id)


async def _cleanup_old_paginated_messages(db: Database, bot: Bot) -> None:
    cutoff = _paginated_metadata_cutoff()
    states = db.list_paginated_message_states_before(cutoff)
    if not states:
        return

    logger.info("Limpiando %s botoneras vencidas.", len(states))
    for state in states:
        await _delete_paginated_message_by_id(
            db=db,
            bot=bot,
            chat_id=_parse_chat_id(state.chat_id),
            message_id=state.message_id,
        )


def _paginated_metadata_cutoff() -> str:
    return (datetime.utcnow() - PAGINATED_METADATA_TTL).strftime("%Y-%m-%d %H:%M:%S")


def _is_paginated_state_expired(created_at: str) -> bool:
    try:
        created = datetime.fromisoformat(created_at.replace(" ", "T"))
    except ValueError:
        logger.warning("Fecha invalida en metadata de botonera: %s", created_at)
        return False

    return datetime.utcnow() - created > PAGINATED_METADATA_TTL


async def _edit_paginated_message(
    db: Database,
    message: Message,
    message_id: str,
    page: int,
    unlocked: bool,
) -> None:
    state = db.get_paginated_message_state(str(message.chat.id), message_id)
    if state is None:
        return

    content = json.loads(state.content_json)
    rendered = render_page(content["header"], content["lines"], page=page)
    db.set_paginated_message_page(str(message.chat.id), message_id, rendered.page)
    await message.edit_text(
        text=rendered.text,
        reply_markup=build_keyboard(message_id, rendered.page, rendered.total_pages, unlocked=unlocked),
    )


def _register_chat_from_message(message: Message, db: Database) -> None:
    chat = message.chat
    if chat is None:
        return

    db.register_chat(
        chat_id=str(chat.id),
        chat_type=chat.type,
        title=chat.title,
    )


def _handle_chat_migration(message: Message, db: Database) -> bool:
    old_chat_id = message.chat.id if message.chat is not None else None
    new_chat_id = message.migrate_to_chat_id

    if old_chat_id is None or new_chat_id is None:
        return False

    db.migrate_chat_id(old_chat_id=str(old_chat_id), new_chat_id=str(new_chat_id))
    logger.info("Chat migrado de %s a %s.", old_chat_id, new_chat_id)
    return True


def _register_bot_added_event(message: Message, db: Database, bot_user_id: str) -> None:
    chat = message.chat
    from_user = message.from_user
    if chat is None or from_user is None:
        return

    was_bot_added = any(str(member.id) == bot_user_id for member in (message.new_chat_members or []))
    if not was_bot_added:
        return

    db.get_or_create_user(str(from_user.id), _display_name(from_user), from_user.username)
    db.register_chat(
        chat_id=str(chat.id),
        chat_type=chat.type,
        title=chat.title,
        added_by_user_id=str(from_user.id),
    )


def _register_bot_removed_event(message: Message, db: Database, bot_user_id: str) -> None:
    chat = message.chat
    if chat is None:
        return

    left_member = message.left_chat_member
    if left_member is not None and str(left_member.id) == bot_user_id:
        db.mark_chat_inactive(str(chat.id), "left_chat_member")


async def _resolve_user_level(
    user_id: str,
    chat: Chat,
    db: Database,
    bot: Bot,
    dev_user_ids: frozenset[str],
) -> UserLevel:
    if user_id in dev_user_ids:
        return UserLevel.DEV

    added_by_user_id = db.get_chat_added_by_user_id(str(chat.id))
    if added_by_user_id == user_id:
        return UserLevel.ADMIN

    if chat.type in {"group", "supergroup"} and await _is_chat_admin(chat.id, user_id, bot):
        return UserLevel.ADMIN

    return UserLevel.COMMON


def _is_command_group_disabled(db: Database, chat: Chat, command_group: str | None) -> bool:
    if command_group is None or chat.type not in {"group", "supergroup"}:
        return False
    return not db.is_command_group_enabled(str(chat.id), command_group)


async def _is_chat_admin(chat_id: int, user_id: str, bot: Bot) -> bool:
    try:
        administrators = await bot.get_chat_administrators(chat_id)
    except TelegramError as exc:
        logger.warning("No pude leer admines del chat %s: %s", chat_id, exc)
        return False

    return any(str(admin.user.id) == user_id for admin in administrators)


async def _send_unhandled_error_event(
    bot: Bot,
    log_chat_id: str | None,
    exc: BaseException,
) -> None:
    trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    if len(trace) > 3200:
        trace = trace[-3200:]

    await _send_log_event(bot, log_chat_id, f"Error no handleado:\n{trace}")


async def _send_log_event(bot: Bot, log_chat_id: str | None, text: str) -> None:
    await _send_log_text_with_truncation(bot, log_chat_id, text)


async def _send_log_text_with_truncation(
    bot: Bot,
    log_chat_id: str | None,
    text: str,
    truncation_notice: str | None = None,
) -> bool:
    if not log_chat_id:
        return False

    try:
        was_truncated = len(text) > TELEGRAM_MESSAGE_LIMIT_CHARS
        await bot.send_message(
            chat_id=_parse_chat_id(log_chat_id),
            text=text[:TELEGRAM_MESSAGE_LIMIT_CHARS],
        )
        if was_truncated and truncation_notice:
            await bot.send_message(chat_id=_parse_chat_id(log_chat_id), text=truncation_notice)
    except (TelegramError, ValueError) as exc:
        logger.warning("No pude enviar evento al canal de logging: %s", exc)
        return False

    return True


async def _send_announcement(
    bot: Bot,
    announcements_chat_id: str | None,
    text: str,
    log_chat_id: str | None = None,
    language: str = DEFAULT_LANGUAGE,
) -> bool:
    if not announcements_chat_id:
        return False

    try:
        was_truncated = len(text) > TELEGRAM_MESSAGE_LIMIT_CHARS
        await bot.send_message(
            chat_id=_parse_chat_id(announcements_chat_id),
            text=text[:TELEGRAM_MESSAGE_LIMIT_CHARS],
        )
        if was_truncated:
            await _send_log_event(bot, log_chat_id, t(language, "long_message.truncated_log"))
    except (TelegramError, ValueError) as exc:
        logger.warning("No pude enviar novedad al canal de anuncios: %s", exc)
        return False

    return True


async def _create_and_send_backup(
    db: Database,
    message: Message,
) -> BackupResult:
    backup_path = db.create_backup(Path("backups"))
    size_bytes = backup_path.stat().st_size

    if size_bytes > TELEGRAM_DOCUMENT_UPLOAD_LIMIT_BYTES:
        return BackupResult(
            path=backup_path,
            size_bytes=size_bytes,
            max_size_bytes=TELEGRAM_DOCUMENT_UPLOAD_LIMIT_BYTES,
            sent=False,
        )

    await message.reply_document(
        document=backup_path,
        caption=t(_chat_language(db, message.chat.id), "backup.caption"),
        do_quote=True,
    )
    return BackupResult(
        path=backup_path,
        size_bytes=size_bytes,
        max_size_bytes=TELEGRAM_DOCUMENT_UPLOAD_LIMIT_BYTES,
        sent=True,
    )


async def _send_debug_update(
    db: Database,
    message: Message,
    update: Update,
) -> bool:
    debug_json = update.to_json(indent=2)
    wrapped_json = f"```json\n{debug_json}\n```"

    try:
        if len(wrapped_json) <= TELEGRAM_MESSAGE_LIMIT_CHARS:
            await message.reply_text(
                text=wrapped_json,
                do_quote=True,
            )
            return True

        debug_dir = Path("debug")
        debug_dir.mkdir(parents=True, exist_ok=True)
        debug_path = debug_dir / f"update-{message.message_id or int(time.time())}.json"
        debug_path.write_text(debug_json, encoding="utf-8")
        await message.reply_document(
            document=debug_path,
            caption=t(_chat_language(db, message.chat.id), "debug.caption"),
            do_quote=True,
        )
        return True
    except (TelegramError, OSError) as exc:
        logger.warning("No pude enviar update de debug: %s", exc)
        return False


async def _leave_chat(db: Database, bot: Bot, chat_id: int) -> bool:
    try:
        await bot.leave_chat(chat_id)
    except TelegramError as exc:
        logger.warning("No pude salir del chat %s: %s", chat_id, exc)
        return False

    db.mark_chat_inactive(str(chat_id), "left_by_command")
    return True


def _parse_chat_id(raw_chat_id: str) -> int | str:
    if raw_chat_id.lstrip("-").isdigit():
        return int(raw_chat_id)
    return raw_chat_id


def _chat_language(db: Database, chat_id: int | str | None) -> str:
    if chat_id is None:
        return DEFAULT_LANGUAGE
    return db.get_chat_settings(str(chat_id)).language




def _is_bot_removed_error(exc: TelegramError) -> bool:
    if isinstance(exc, Forbidden):
        return True
    if not isinstance(exc, BadRequest):
        return False
    message = str(exc).lower()
    markers = [
        "bot was blocked by the user",
        "bot was kicked",
        "bot is not a member",
        "chat not found",
        "forbidden",
    ]
    return any(marker in message for marker in markers)


def _today_key() -> str:
    try:
        now = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))
    except Exception:
        now = datetime.now().astimezone()
    return now.date().isoformat()
