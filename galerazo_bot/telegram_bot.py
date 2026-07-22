from __future__ import annotations

import asyncio
import json
import logging
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram import Bot, Chat, ChatMember, Message, MessageEntity, Update, User
from telegram.error import BadRequest, Conflict, Forbidden, TelegramError
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
from .cloud_billing import (
    GoogleCloudBillingConfig,
    GoogleCloudBillingReader,
    format_google_cloud_billing_report,
    parse_report_time,
)
from .commands import COMMANDS, get_command, handle_command_async, is_command_invocation
from .config import Settings, load_settings
from .database import Database, Trigger
from .expenses import (
    ExpenseSheetStatus,
    ExpenseSubmissionResult,
    ExpenseSyncResult,
    fallback_sheet_detail,
    format_amount,
)
from .galeraza import build_galeraza_header, build_galeraza_lines, render_galeraza_page
from .google_sheets import GoogleSheetsConfig, GoogleSheetsExpenseWriter
from .i18n import DEFAULT_LANGUAGE, t
from .instance_lock import SingleInstance
from .integration_status import save_logging_status
from .logging_utils import configure_logging
from .media_moderation import OpenAIMediaModerator, trigger_media_kind
from .pagination import BUTTON_PREFIX, build_keyboard, parse_callback_data, render_page
from .roles import BackupResult, RussianRouletteHitResult, TriggerModerationResult, TriggerPayload, UserLevel
from .runtime import ensure_python_version
from .update_processor import PerChatUpdateProcessor


logger = logging.getLogger(__name__)
TELEGRAM_DOCUMENT_UPLOAD_LIMIT_BYTES = 50 * 1024 * 1024
TELEGRAM_FILE_DOWNLOAD_LIMIT_BYTES = 20 * 1024 * 1024
TELEGRAM_MESSAGE_LIMIT_CHARS = 4096
PAGINATED_METADATA_TTL = timedelta(days=14)
ARGENTINA_TIMEZONE = ZoneInfo("America/Argentina/Buenos_Aires")
POLLING_OPTIONS = {
    "allowed_updates": Update.ALL_TYPES,
    "drop_pending_updates": False,
}


def _bold_first_line_entities(text: str) -> list[MessageEntity]:
    title = text.partition("\n")[0]
    if not title:
        return []
    utf16_length = len(title.encode("utf-16-le")) // 2
    return [MessageEntity(type=MessageEntity.BOLD, offset=0, length=utf16_length)]


@dataclass(frozen=True)
class BotState:
    db: Database
    settings: Settings
    bot_user_id: str
    expense_sheet_writer: GoogleSheetsExpenseWriter
    media_moderator: OpenAIMediaModerator


def main() -> None:
    ensure_python_version()
    configure_logging()

    settings = load_settings()
    if not settings.telegram_bot_token:
        raise RuntimeError("Falta TELEGRAM_BOT_TOKEN en el archivo .env")

    instance = SingleInstance(f"telegram-bot-token:{settings.telegram_bot_token}")
    if not instance.acquire():
        raise RuntimeError(
            "Ya hay otra instancia local de este bot en ejecucion. "
            "Apagala desde el panel que la inicio antes de volver a encenderla."
        )

    try:
        db = Database(settings.database_path)
        application = _build_application(settings.telegram_bot_token, db)
        application.bot_data["settings"] = settings
        application.bot_data["db"] = db

        _register_handlers(application)
        application.add_error_handler(_handle_error)

        logger.info("Galerazo Bot escuchando mensajes de Telegram.")
        application.run_polling(**POLLING_OPTIONS)
    finally:
        instance.release()


def _build_application(token: str, db: Database) -> Application:
    return (
        ApplicationBuilder()
        .token(token)
        .post_init(_post_init)
        .concurrent_updates(PerChatUpdateProcessor(db.resolve_chat_id))
        .build()
    )


def _register_handlers(application: Application) -> None:
    application.add_handler(MessageHandler(filters.ALL, _preprocess_message), group=0)

    for command_name in COMMANDS:
        application.add_handler(CommandHandler(command_name, _command_entrypoint), group=1)

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _text_command_entrypoint), group=1)
    application.add_handler(CallbackQueryHandler(_callback_query_entrypoint, pattern=f"^{BUTTON_PREFIX}:"), group=1)
    application.add_handler(CallbackQueryHandler(_config_callback_entrypoint, pattern=f"^{CONFIG_PREFIX}:"), group=1)
    application.add_handler(ChatMemberHandler(_my_chat_member_entrypoint, ChatMemberHandler.MY_CHAT_MEMBER), group=1)


async def _post_init(application: Application) -> None:
    settings = application.bot_data["settings"]
    db = application.bot_data["db"]
    bot_user = await application.bot.get_me()
    application.bot_data["state"] = BotState(
        db=db,
        settings=settings,
        bot_user_id=str(bot_user.id),
        expense_sheet_writer=GoogleSheetsExpenseWriter(
            GoogleSheetsConfig(
                credentials_json_path=settings.google_sheets_credentials_json_path,
                spreadsheet_id=settings.google_sheets_spreadsheet_id,
                worksheet_name=settings.google_sheets_worksheet_name,
            )
        ),
        media_moderator=OpenAIMediaModerator(settings.openai_api_key),
    )

    await _cleanup_old_paginated_messages(db, application.bot)
    await _send_log_event(application.bot, settings.telegram_log_chat_id, "Galerazo Bot iniciado.")
    _schedule_google_cloud_billing_report(application, settings)


def _schedule_google_cloud_billing_report(
    application: Application,
    settings: Settings,
) -> bool:
    if not settings.telegram_log_chat_id:
        logger.info(
            "Reporte diario de Google Cloud Billing desactivado: falta el canal de logging."
        )
        return False
    config = GoogleCloudBillingConfig(
        query_project_id=settings.google_cloud_billing_project_id,
        export_table=settings.google_cloud_billing_table,
    )
    if not config.is_configured:
        logger.info("Reporte diario de Google Cloud Billing no configurado.")
        return False

    try:
        reader = GoogleCloudBillingReader(config)
        report_time = parse_report_time(settings.google_cloud_billing_report_time)
    except ValueError as exc:
        logger.error("Configuracion invalida del reporte de Google Cloud Billing: %s", exc)
        return False

    job_queue = application.job_queue
    if job_queue is None:
        raise RuntimeError(
            "python-telegram-bot debe instalarse con el extra job-queue"
        )
    job_queue.run_daily(
        _google_cloud_billing_report_job,
        time=report_time,
        data=reader,
        name="google-cloud-monthly-spend",
        job_kwargs={
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 6 * 60 * 60,
        },
    )
    logger.info(
        "Reporte diario de Google Cloud Billing programado para las %s (Argentina).",
        settings.google_cloud_billing_report_time,
    )
    return True


async def _google_cloud_billing_report_job(
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    job = context.job
    reader = job.data if job is not None else None
    if not isinstance(reader, GoogleCloudBillingReader):
        logger.error("El job de Google Cloud Billing no tiene un lector valido.")
        return
    settings = context.application.bot_data["settings"]
    await _send_google_cloud_billing_report(
        context.bot,
        settings.telegram_log_chat_id,
        reader,
    )


async def _send_google_cloud_billing_report(
    bot: Bot,
    log_chat_id: str | None,
    reader: GoogleCloudBillingReader,
) -> bool:
    try:
        report = await reader.get_month_to_date()
        text = format_google_cloud_billing_report(report)
    except Exception as exc:
        logger.exception("No pude consultar Google Cloud Billing: %s", exc)
        text = (
            "Google Cloud - gasto mensual\n"
            "No pude consultar el gasto. Revisa la exportacion de Billing, "
            "los permisos de BigQuery y los logs del bot."
        )
    return await _send_log_event(bot, log_chat_id, text)


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
    if _is_user_restricted_in_message_chat(state.db, message, str(user.id)):
        return

    if _is_galeraza_candidate(update, message, user):
        await _maybe_award_daily_galeraza(
            db=state.db,
            message=message,
            user_id=str(user.id),
        )

    text = message.text or message.caption
    if not text or is_command_invocation(text):
        return

    await _maybe_send_triggered_messages(
        db=state.db,
        bot=context.bot,
        message=message,
    )

    state.db.save_incoming_message(sender_id=str(user.id), text=text, chat_id=str(chat.id))


async def _maybe_send_triggered_messages(
    db: Database,
    bot: Bot,
    message: Message,
) -> None:
    if message.chat.type not in {"group", "supergroup"}:
        return
    if not db.is_command_group_enabled(str(message.chat.id), "triggers"):
        return

    text = message.text or message.caption
    if not text:
        return

    normalized_text = text.casefold()
    for trigger in db.list_triggers(str(message.chat.id)):
        if trigger.trigger_name not in normalized_text:
            continue
        try:
            await _send_trigger_message(bot, message.chat.id, trigger)
        except TelegramError as exc:
            logger.warning("No pude enviar trigger %s en chat %s: %s", trigger.display_name, message.chat.id, exc)


async def _send_trigger_message(bot: Bot, chat_id: int, trigger: Trigger) -> None:
    if trigger.media_type == "photo" and trigger.file_id:
        await bot.send_photo(chat_id=chat_id, photo=trigger.file_id, caption=trigger.caption)
        return
    if trigger.media_type == "video" and trigger.file_id:
        await bot.send_video(chat_id=chat_id, video=trigger.file_id, caption=trigger.caption)
        return
    if trigger.media_type == "animation" and trigger.file_id:
        await bot.send_animation(chat_id=chat_id, animation=trigger.file_id, caption=trigger.caption)
        return
    if trigger.media_type == "audio" and trigger.file_id:
        await bot.send_audio(chat_id=chat_id, audio=trigger.file_id, caption=trigger.caption)
        return
    if trigger.media_type == "voice" and trigger.file_id:
        await bot.send_voice(chat_id=chat_id, voice=trigger.file_id, caption=trigger.caption)
        return
    if trigger.media_type == "document" and trigger.file_id:
        await bot.send_document(chat_id=chat_id, document=trigger.file_id, caption=trigger.caption)
        return
    if trigger.media_type == "video_note" and trigger.file_id:
        await bot.send_video_note(chat_id=chat_id, video_note=trigger.file_id)
        return
    if trigger.media_type == "sticker" and trigger.file_id:
        await bot.send_sticker(chat_id=chat_id, sticker=trigger.file_id)
        return
    if trigger.media_type == "dice" and trigger.text:
        await bot.send_dice(chat_id=chat_id, emoji=trigger.text)
        return
    payload = _trigger_payload_data(trigger)
    if trigger.media_type == "contact" and payload:
        await bot.send_contact(chat_id=chat_id, **payload)
        return
    if trigger.media_type == "location" and payload:
        await bot.send_location(chat_id=chat_id, **payload)
        return
    if trigger.media_type == "venue" and payload:
        await bot.send_venue(chat_id=chat_id, **payload)
        return
    if trigger.media_type == "poll" and payload:
        await bot.send_poll(chat_id=chat_id, **payload)
        return
    if trigger.text:
        await bot.send_message(chat_id=chat_id, text=trigger.text[:TELEGRAM_MESSAGE_LIMIT_CHARS])


def _trigger_payload_data(trigger: Trigger) -> dict[str, object] | None:
    if not trigger.payload_json:
        return None
    try:
        payload = json.loads(trigger.payload_json)
    except (TypeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


async def _command_entrypoint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _handle_command_update(update, context)


async def _text_command_entrypoint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None or not message.text:
        return

    if not is_command_invocation(message.text):
        return

    await _handle_command_update(update, context)


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
    if _is_user_restricted_in_message_chat(state.db, message, str(user.id)):
        return

    user_level = UserLevel.COMMON
    command = get_command(message.text)
    if command is not None and _is_command_group_disabled(state.db, chat, command.configurable_group):
        return

    if command is not None:
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
        reply_to_trigger_payload=_trigger_payload_from_message(message.reply_to_message),
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
        submit_expense=lambda currency, amount_cents, payment_method, source, description: _submit_expense(
            db=state.db,
            writer=state.expense_sheet_writer,
            message=message,
            user=user,
            currency=currency,
            amount_cents=int(amount_cents),
            payment_method=payment_method,
            source=source,
            description=description,
        ),
        sync_expenses=lambda: _sync_pending_expenses(
            db=state.db,
            writer=state.expense_sheet_writer,
            message=message,
        ),
        get_expense_sheet_status=lambda: _build_expense_sheet_status(
            db=state.db,
            writer=state.expense_sheet_writer,
            chat_id=str(chat.id),
        ),
        create_backup=lambda: _create_and_send_backup(state.db, message),
        send_debug_update=lambda: _send_debug_update(state.db, message, update),
        send_galerazas=lambda: _send_galerazas(state.db, message, str(user.id)),
        send_config_menu=lambda: _send_config_menu(state.db, message),
        leave_chat=lambda: _leave_chat(state.db, context.bot, chat.id),
        can_run_russian_roulette=lambda: _bot_can_ban_members(
            context.bot,
            chat.id,
            state.bot_user_id,
        ),
        resolve_russian_roulette_hit=lambda target_user_id: _resolve_russian_roulette_hit(
            context.bot,
            chat.id,
            target_user_id,
            state.bot_user_id,
            state.settings.telegram_dev_user_ids,
        ),
        moderate_trigger_payload=lambda payload: _moderate_trigger_payload(
            context.bot,
            state.media_moderator,
            payload,
        ),
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
    if _is_user_restricted_in_callback_chat(state.db, callback_query, str(user.id)):
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
    if _is_user_restricted_in_callback_chat(state.db, callback_query, str(user.id)):
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
    if isinstance(context.error, Conflict):
        logger.error(
            "Telegram rechazo el polling porque otra instancia externa usa este token. "
            "Revisar otros equipos, servicios o deploys activos."
        )
        context.application.stop_running()
    settings = context.application.bot_data.get("settings")
    if settings is None or context.error is None:
        return
    await _send_unhandled_error_event(
        context.bot,
        settings.telegram_log_chat_id,
        context.error,
        update,
    )


def _display_name(user: User | None) -> str | None:
    if user is None:
        return None
    return user.full_name or user.username


def _is_user_restricted_in_message_chat(db: Database, message: Message, user_id: str) -> bool:
    if message.chat.type not in {"group", "supergroup"}:
        return False
    return db.is_user_restricted_in_chat(str(message.chat.id), user_id)


def _is_user_restricted_in_callback_chat(db: Database, callback_query, user_id: str) -> bool:
    message = callback_query.message
    if message is None or message.chat.type not in {"group", "supergroup"}:
        return False
    return db.is_user_restricted_in_chat(str(message.chat.id), user_id)


def _trigger_payload_from_message(message: Message | None) -> TriggerPayload | None:
    if message is None:
        return None
    if message.text:
        return TriggerPayload(text=message.text)
    if message.photo:
        photo = message.photo[-1]
        return TriggerPayload(
            media_type="photo",
            file_id=photo.file_id,
            caption=message.caption,
            mime_type="image/jpeg",
            moderation_file_size=getattr(photo, "file_size", None),
        )
    if message.video:
        return TriggerPayload(
            media_type="video",
            file_id=message.video.file_id,
            caption=message.caption,
            mime_type=getattr(message.video, "mime_type", None) or "video/mp4",
            moderation_file_size=getattr(message.video, "file_size", None),
        )
    if message.animation:
        return TriggerPayload(media_type="animation", file_id=message.animation.file_id, caption=message.caption)
    if message.audio:
        return TriggerPayload(media_type="audio", file_id=message.audio.file_id, caption=message.caption)
    if message.voice:
        return TriggerPayload(media_type="voice", file_id=message.voice.file_id, caption=message.caption)
    if message.document:
        return TriggerPayload(
            media_type="document",
            file_id=message.document.file_id,
            caption=message.caption,
            mime_type=getattr(message.document, "mime_type", None),
            moderation_file_size=getattr(message.document, "file_size", None),
        )
    if message.video_note:
        return TriggerPayload(
            media_type="video_note",
            file_id=message.video_note.file_id,
            mime_type="video/mp4",
            moderation_file_size=getattr(message.video_note, "file_size", None),
        )
    if message.sticker:
        thumbnail = getattr(message.sticker, "thumbnail", None)
        return TriggerPayload(
            media_type="sticker",
            file_id=message.sticker.file_id,
            mime_type="image/jpeg" if thumbnail is not None else "image/webp",
            moderation_file_id=getattr(thumbnail, "file_id", None),
            moderation_file_size=(
                getattr(thumbnail, "file_size", None)
                if thumbnail is not None
                else getattr(message.sticker, "file_size", None)
            ),
        )
    if message.dice:
        return TriggerPayload(text=message.dice.emoji, media_type="dice")
    if message.contact:
        return TriggerPayload(
            media_type="contact",
            data={
                key: value
                for key, value in {
                    "phone_number": message.contact.phone_number,
                    "first_name": message.contact.first_name,
                    "last_name": message.contact.last_name,
                    "vcard": message.contact.vcard,
                }.items()
                if value is not None
            },
        )
    if message.venue:
        return TriggerPayload(
            media_type="venue",
            data={
                key: value
                for key, value in {
                    "latitude": message.venue.location.latitude,
                    "longitude": message.venue.location.longitude,
                    "title": message.venue.title,
                    "address": message.venue.address,
                    "foursquare_id": message.venue.foursquare_id,
                    "foursquare_type": message.venue.foursquare_type,
                    "google_place_id": message.venue.google_place_id,
                    "google_place_type": message.venue.google_place_type,
                }.items()
                if value is not None
            },
        )
    if message.location:
        return TriggerPayload(
            media_type="location",
            data={
                key: value
                for key, value in {
                    "latitude": message.location.latitude,
                    "longitude": message.location.longitude,
                    "horizontal_accuracy": message.location.horizontal_accuracy,
                }.items()
                if value is not None
            },
        )
    if message.poll:
        poll_data: dict[str, object] = {
            "question": message.poll.question,
            "options": [option.text for option in message.poll.options],
            "is_anonymous": message.poll.is_anonymous,
            "type": message.poll.type,
            "allows_multiple_answers": message.poll.allows_multiple_answers,
        }
        if message.poll.correct_option_id is not None:
            poll_data["correct_option_id"] = message.poll.correct_option_id
        if message.poll.explanation:
            poll_data["explanation"] = message.poll.explanation
        return TriggerPayload(media_type="poll", data=poll_data)
    return None


async def _moderate_trigger_payload(
    bot: Bot,
    moderator: OpenAIMediaModerator,
    payload: TriggerPayload,
) -> TriggerModerationResult:
    if not moderator.enabled:
        return TriggerModerationResult.SKIPPED

    media_kind = trigger_media_kind(payload.media_type, payload.mime_type)
    if media_kind is None:
        return TriggerModerationResult.SKIPPED
    if (
        payload.moderation_file_size is not None
        and payload.moderation_file_size > TELEGRAM_FILE_DOWNLOAD_LIMIT_BYTES
    ):
        return TriggerModerationResult.TOO_LARGE

    file_id = payload.moderation_file_id or payload.file_id
    if not file_id:
        return TriggerModerationResult.ERROR

    downloaded: bytearray | None = None
    try:
        telegram_file = await bot.get_file(file_id)
        downloaded = await telegram_file.download_as_bytearray()
        if media_kind == "image":
            return await moderator.moderate_image(downloaded)
        return await moderator.moderate_video(downloaded)
    except TelegramError as exc:
        logger.warning(
            "No se pudo descargar media de Telegram para moderacion (%s).",
            type(exc).__name__,
        )
        return TriggerModerationResult.ERROR
    finally:
        if downloaded is not None:
            downloaded[:] = b"\x00" * len(downloaded)
            downloaded.clear()


async def _maybe_award_daily_galeraza(
    db: Database,
    message: Message,
    user_id: str,
) -> None:
    if message.chat.type not in {"group", "supergroup"}:
        return
    if not db.is_command_group_enabled(str(message.chat.id), "galeraza"):
        return

    message_date = _telegram_message_datetime(message)
    game_date = _galeraza_game_date(message)
    awarded = db.try_award_daily_galeraza(
        chat_id=str(message.chat.id),
        game_date=game_date,
        user_id=user_id,
        message_id=str(message.message_id),
        message_date=message_date.isoformat(),
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
    lines = build_galeraza_lines(scores, language)
    page = render_galeraza_page(scores, page=1, language=language)
    content_json = json.dumps({"header": build_galeraza_header(language), "lines": lines}, ensure_ascii=False)
    try:
        entities = _bold_first_line_entities(page.text)
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


async def _submit_expense(
    db: Database,
    writer: GoogleSheetsExpenseWriter,
    message: Message,
    user: User,
    currency: str,
    amount_cents: int,
    payment_method: str,
    source: str,
    description: str,
) -> ExpenseSubmissionResult:
    expense = db.add_expense(
        chat_id=str(message.chat.id),
        user_id=str(user.id),
        amount_cents=amount_cents,
        currency=currency,
        payment_method=payment_method,
        source=source,
        description=description,
    )

    row = [
        str(expense.expense_id),
        expense.created_at,
        expense.chat_id,
        message.chat.title or "-",
        expense.user_id,
        f"@{expense.username}" if expense.username else "-",
        expense.display_name or "-",
        format_amount(expense.amount_cents, expense.currency),
        expense.currency,
        expense.payment_method,
        expense.source,
        expense.description,
    ]
    synced, error = await asyncio.to_thread(writer.append_expense_row, row)
    if synced:
        db.mark_expense_synced(expense.expense_id)
        return ExpenseSubmissionResult(expense_id=expense.expense_id, synced=True, configured=True)

    db.mark_expense_failed(expense.expense_id, error)
    return ExpenseSubmissionResult(
        expense_id=expense.expense_id,
        synced=False,
        configured=writer.is_configured(),
        error=error,
    )


def _build_expense_sheet_status(
    db: Database,
    writer: GoogleSheetsExpenseWriter,
    chat_id: str,
) -> ExpenseSheetStatus:
    configured = writer.is_configured()
    ready = writer.is_ready()
    return ExpenseSheetStatus(
        enabled_for_chat=db.is_command_group_enabled(chat_id, "gastos"),
        configured=configured,
        ready=ready,
        worksheet_name=writer.worksheet_name if configured else None,
        pending_count=db.count_pending_expenses(chat_id),
        detail=fallback_sheet_detail(_chat_language(db, chat_id), configured, ready),
    )


async def _sync_pending_expenses(
    db: Database,
    writer: GoogleSheetsExpenseWriter,
    message: Message,
) -> ExpenseSyncResult:
    if not writer.is_configured():
        return ExpenseSyncResult(configured=False, synced_count=0, failed_count=0)

    pending_expenses = db.list_pending_expenses(str(message.chat.id))
    synced_count = 0
    failed_count = 0
    last_error = None
    for expense in pending_expenses:
        row = [
            str(expense.expense_id),
            expense.created_at,
            expense.chat_id,
            message.chat.title or "-",
            expense.user_id,
            f"@{expense.username}" if expense.username else "-",
            expense.display_name or "-",
            format_amount(expense.amount_cents, expense.currency),
            expense.currency,
            expense.payment_method,
            expense.source,
            expense.description,
        ]
        synced, error = await asyncio.to_thread(writer.append_expense_row, row)
        if synced:
            db.mark_expense_synced(expense.expense_id)
            synced_count += 1
            continue
        db.mark_expense_failed(expense.expense_id, error)
        failed_count += 1
        last_error = error

    return ExpenseSyncResult(
        configured=True,
        synced_count=synced_count,
        failed_count=failed_count,
        last_error=last_error,
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

    if action == "close":
        await message.delete()
        return t(language, "config.closed")

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
    edit_options = {}
    if state.list_type == "galeraza":
        edit_options["entities"] = _bold_first_line_entities(rendered.text)
    await message.edit_text(
        text=rendered.text,
        reply_markup=build_keyboard(message_id, rendered.page, rendered.total_pages, unlocked=unlocked),
        **edit_options,
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
    if message.chat is None:
        return False

    if message.migrate_to_chat_id is not None:
        old_chat_id = message.chat.id
        new_chat_id = message.migrate_to_chat_id
    elif message.migrate_from_chat_id is not None:
        old_chat_id = message.migrate_from_chat_id
        new_chat_id = message.chat.id
    else:
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


async def _bot_can_ban_members(bot: Bot, chat_id: int, bot_user_id: str) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, int(bot_user_id))
    except TelegramError as exc:
        logger.warning("No pude validar permisos de ruleta rusa en chat %s: %s", chat_id, exc)
        return False

    if member.status == ChatMember.OWNER:
        return True
    return member.status == ChatMember.ADMINISTRATOR and bool(
        getattr(member, "can_restrict_members", False)
    )


async def _resolve_russian_roulette_hit(
    bot: Bot,
    chat_id: int,
    target_user_id: str,
    bot_user_id: str,
    dev_user_ids: frozenset[str],
) -> RussianRouletteHitResult:
    if target_user_id == bot_user_id:
        return RussianRouletteHitResult.BOT_IMMUNE
    if target_user_id in dev_user_ids:
        return RussianRouletteHitResult.DEV_IMMUNE

    try:
        member = await bot.get_chat_member(chat_id, int(target_user_id))
        if member.status in {ChatMember.OWNER, ChatMember.ADMINISTRATOR}:
            return RussianRouletteHitResult.ADMIN_IMMUNE
        await bot.ban_chat_member(
            chat_id=chat_id,
            user_id=int(target_user_id),
            revoke_messages=False,
        )
    except TelegramError as exc:
        logger.warning(
            "No pude resolver el disparo de ruleta rusa para %s en chat %s: %s",
            target_user_id,
            chat_id,
            exc,
        )
        return RussianRouletteHitResult.FAILED
    return RussianRouletteHitResult.BANNED


async def _send_unhandled_error_event(
    bot: Bot,
    log_chat_id: str | None,
    exc: BaseException,
    update: object = None,
) -> None:
    trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    if len(trace) > 2200:
        trace = trace[-2200:]

    update_json = _serialize_update(update)
    text = f"Error no handleado:\n{trace}\nUpdate JSON:\n{update_json}"
    await _send_log_text_with_truncation(
        bot,
        log_chat_id,
        text,
        truncation_notice="El reporte de error y su update fueron truncados al limite de Telegram.",
    )


async def _send_log_event(bot: Bot, log_chat_id: str | None, text: str) -> bool:
    return await _send_log_text_with_truncation(bot, log_chat_id, text)


async def _send_log_text_with_truncation(
    bot: Bot,
    log_chat_id: str | None,
    text: str,
    truncation_notice: str | None = None,
) -> bool:
    if not log_chat_id:
        save_logging_status(False, "El canal de logging no está configurado.")
        return False

    try:
        was_truncated = len(text) > TELEGRAM_MESSAGE_LIMIT_CHARS
        await bot.send_message(
            chat_id=_parse_chat_id(log_chat_id),
            text=text[:TELEGRAM_MESSAGE_LIMIT_CHARS],
        )
        if was_truncated and truncation_notice:
            await bot.send_message(chat_id=_parse_chat_id(log_chat_id), text=truncation_notice)
        save_logging_status(True, "Canal de logging accesible.")
    except (TelegramError, ValueError) as exc:
        logger.warning("No pude enviar evento al canal de logging: %s", exc)
        save_logging_status(
            False,
            "No se pudo acceder al canal configurado. Verificá que el bot sea miembro y tenga permiso para enviar mensajes.",
        )
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
    debug_json = _serialize_update(update)

    try:
        if len(debug_json) <= TELEGRAM_MESSAGE_LIMIT_CHARS:
            await message.reply_text(
                text=debug_json,
                do_quote=True,
            )
            return True

        debug_dir = Path("debug")
        debug_dir.mkdir(parents=True, exist_ok=True)
        update_id = update.update_id if isinstance(update, Update) else None
        update_label = str(update_id) if update_id is not None else "sin id"
        debug_path = debug_dir / f"Debug de la update {update_label}"
        debug_path.write_text(debug_json, encoding="utf-8")
        await message.reply_document(
            document=debug_path,
            do_quote=True,
        )
        return True
    except (TelegramError, OSError) as exc:
        logger.warning("No pude enviar update de debug: %s", exc)
        return False


def _serialize_update(update: object) -> str:
    if isinstance(update, Update):
        payload = update.to_dict()
    elif update is None:
        payload = None
    else:
        payload = update
    return json.dumps(payload, ensure_ascii=False, indent=2, default=repr)


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


def _is_galeraza_candidate(update: Update, message: Message, user: User) -> bool:
    return not user.is_bot and update.message is message


def _telegram_message_datetime(message: Message) -> datetime:
    message_date = message.date
    if message_date.tzinfo is None:
        return message_date.replace(tzinfo=timezone.utc)
    return message_date


def _galeraza_game_date(message: Message) -> str:
    return _telegram_message_datetime(message).astimezone(ARGENTINA_TIMEZONE).date().isoformat()
