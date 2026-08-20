from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

from telegram import (
    Bot,
    BotCommand,
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeDefault,
    Chat,
    ChatMember,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    LinkPreviewOptions,
    Message,
    Update,
    User,
)
from telegram.error import BadRequest, Conflict, Forbidden, NetworkError, TelegramError, TimedOut
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackContext,
    ContextTypes,
)

from .chat_config import (
    CONFIG_PREFIX,
    build_announcements_menu,
    build_command_group_menu,
    build_command_groups_menu,
    build_hisopo_menu,
    build_language_menu,
    build_main_menu,
    command_group_label,
    is_valid_command_group,
    is_valid_language,
    parse_config_callback,
)
from .chat_migration import chat_migration_ids
from .cloud_billing import (
    GoogleCloudBillingConfig,
    GoogleCloudBillingReader,
    format_google_cloud_billing_report,
    parse_report_time,
)
from .announcements import AnnouncementBroadcastResult, announcement_fits, format_announcement
from .commands import (
    COMMANDS,
    SYMBOL_COMMAND_PREFIXES,
    get_command,
    handle_command_async,
    is_command_invocation,
)
from .config import Settings, load_settings
from .database import Database, HisopoSchedule, HisopoSpawn, Trigger
from .expenses import (
    ExpenseSheetStatus,
    ExpenseSubmissionResult,
    ExpenseSyncResult,
    fallback_sheet_detail,
    format_amount,
)
from .command_handlers.galerazas import (
    galeraza_game_date as _galeraza_game_date,
    is_galeraza_candidate as _is_galeraza_candidate,
    maybe_award_daily_galeraza as _maybe_award_daily_galeraza,
    send_galerazas as _send_galerazas,
    telegram_message_datetime as _telegram_message_datetime,
)
from .command_handlers.hisopos import send_hisopos as _send_hisopos
from .handler_registration import register_handlers
from .hisopos import (
    COMMON_HISOPO,
    HISOPO_CALLBACK_PREFIX,
    HISOPO_CAPTURE_CALLBACK,
    hisopo_kind_for_spawn,
    is_fleeting_window_expired,
    radioactive_points_at,
    random_next_day_datetime,
    select_hisopo_spawn,
    should_spawn_hisopo,
)
from .google_sheets import GoogleSheetsConfig, GoogleSheetsExpenseWriter
from .i18n import DEFAULT_LANGUAGE, t
from .instance_lock import SingleInstance
from .integration_status import save_logging_status
from .logging_utils import configure_logging
from .media_moderation import OpenAIMediaModerator, trigger_media_kind
from .pagination import (
    BUTTON_PREFIX,
    bold_first_line_entities as _bold_first_line_entities,
    build_keyboard,
    parse_callback_data,
    render_page,
    render_prebuilt_pages,
)
from .roles import BackupResult, RussianRouletteHitResult, TriggerModerationResult, TriggerPayload, UserLevel
from .runtime import ensure_python_version
from .telegram_retry import build_retrying_ext_bot
from .update_processor import PerChatUpdateProcessor
from .versioning import CURRENT_VERSION, pending_release_notes


logger = logging.getLogger(__name__)
TELEGRAM_DOCUMENT_UPLOAD_LIMIT_BYTES = 50 * 1024 * 1024
TELEGRAM_FILE_DOWNLOAD_LIMIT_BYTES = 20 * 1024 * 1024
TELEGRAM_MESSAGE_LIMIT_CHARS = 4096
TELEGRAM_DOCUMENT_TIMEOUT_SECONDS = 30
TELEGRAM_REQUEST_TIMEOUT_SECONDS = 30
PAGINATED_METADATA_TTL = timedelta(days=14)
RESTART_CONFIRMATION_TTL = timedelta(minutes=5)
RESTART_CALLBACK_PREFIX = "restart"
SHUTDOWN_CALLBACK_PREFIX = "shutdown"
UPDATE_DRAIN_TIMEOUT_SECONDS = 60
DISABLED_LINK_PREVIEW_OPTIONS = LinkPreviewOptions(is_disabled=True)
BOTFATHER_HIDDEN_COMMANDS = frozenset(
    {
        "habilitargastos",
        "deshabilitargastos",
        "gasto",
        "ultimosgastos",
        "estadogastos",
        "sincronizargastos",
    }
)
POLLING_OPTIONS = {
    "allowed_updates": Update.ALL_TYPES,
    "drop_pending_updates": False,
}
PANEL_MANAGED_ENV = "GALERAZO_PANEL_MANAGED"
PANEL_PID_PATH = Path(__file__).resolve().parent.parent / "data" / "bot.pid"
PANEL_RESTART_PATH = PANEL_PID_PATH.with_suffix(".restart")


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
        _record_panel_managed_pid()
        db = Database(settings.database_path)
        application = _build_application(settings.telegram_bot_token, db)
        application.bot_data["settings"] = settings
        application.bot_data["db"] = db

        _register_handlers(application)
        application.add_error_handler(_handle_error)

        logger.info("Galerazo Bot escuchando mensajes de Telegram.")
        application.run_polling(**POLLING_OPTIONS)
        if application.bot_data.get("restart_requested") is True:
            logger.info("Reiniciando Galerazo Bot por confirmacion de desarrollo.")
            _mark_panel_restart_pending()
            os.execv(sys.executable, [sys.executable, *sys.argv])
    finally:
        instance.release()


def _record_panel_managed_pid() -> None:
    if os.environ.get(PANEL_MANAGED_ENV) != "1":
        return
    PANEL_PID_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = PANEL_PID_PATH.with_suffix(".tmp")
    temporary_path.write_text(str(os.getpid()), encoding="ascii")
    temporary_path.replace(PANEL_PID_PATH)
    PANEL_RESTART_PATH.unlink(missing_ok=True)


def _mark_panel_restart_pending() -> None:
    if os.environ.get(PANEL_MANAGED_ENV) == "1":
        PANEL_RESTART_PATH.touch()


def _build_application(token: str, db: Database) -> Application:
    return (
        ApplicationBuilder()
        .bot(build_retrying_ext_bot(token, TELEGRAM_REQUEST_TIMEOUT_SECONDS))
        .post_init(_post_init)
        .concurrent_updates(PerChatUpdateProcessor(db.resolve_chat_id))
        .build()
    )


def _register_handlers(application: Application) -> None:
    register_handlers(
        application,
        command_names=COMMANDS,
        command_prefixes=tuple(prefix for prefix in SYMBOL_COMMAND_PREFIXES if prefix != "/"),
        chat_migration_callback=_chat_migration_entrypoint,
        preprocess_message=_preprocess_message,
        command_callback=_command_entrypoint,
        pagination_callback=_callback_query_entrypoint,
        config_callback=_config_callback_entrypoint,
        hisopo_callback=_hisopo_callback_entrypoint,
        power_callback=_restart_callback_entrypoint,
        chat_member_callback=_my_chat_member_entrypoint,
        pagination_pattern=f"^{BUTTON_PREFIX}:",
        config_pattern=f"^{CONFIG_PREFIX}:",
        hisopo_pattern=f"^{HISOPO_CALLBACK_PREFIX}:",
        power_pattern=f"^({RESTART_CALLBACK_PREFIX}|{SHUTDOWN_CALLBACK_PREFIX}):",
    )


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

    await _sync_botfather_commands(application.bot)
    await _announce_current_release(db, application.bot, settings)
    await _cleanup_old_paginated_messages(db, application.bot)
    _restore_hisopo_jobs(application)
    await _send_log_event(application.bot, settings.telegram_log_chat_id, "Galerazo Bot iniciado.")
    _schedule_google_cloud_billing_report(application, settings)


async def _announce_current_release(db: Database, bot: Bot, settings: Settings) -> bool:
    announced_version = db.get_announced_release_version()
    if announced_version == CURRENT_VERSION:
        return False

    try:
        release_notes = pending_release_notes(announced_version)
    except (OSError, ValueError) as exc:
        error_text = f"No pude leer el changelog de la version {CURRENT_VERSION}: {exc}"
        logger.error(error_text)
        await _send_log_event(bot, settings.telegram_log_chat_id, error_text)
        return False

    result = await _broadcast_announcement(
        db=db,
        bot=bot,
        text=release_notes,
        announcements_chat_id=settings.telegram_announcements_chat_id,
    )
    if result.too_long or not result.announcement_channel_sent:
        return False

    db.set_announced_release_version(CURRENT_VERSION)
    await _send_log_event(
        bot,
        settings.telegram_log_chat_id,
        t(
            DEFAULT_LANGUAGE,
            "announcement.sent",
            sent=result.sent_count,
            skipped=result.skipped_count,
            inactive=result.inactive_count,
            failed=result.failed_count,
            channel="si" if result.announcement_channel_sent else "no",
        ),
    )
    logger.info("Novedades de la version %s enviadas.", CURRENT_VERSION)
    return True


def _suggested_bot_commands(
    language: str,
    max_level: UserLevel,
    include_group_commands: bool,
) -> tuple[BotCommand, ...]:
    commands = []
    for command in COMMANDS.values():
        if command.min_level > max_level or command.hidden or command.name in BOTFATHER_HIDDEN_COMMANDS:
            continue
        if command.name == "config" and include_group_commands and max_level < UserLevel.ADMIN:
            continue
        if command.configurable_group is not None and not include_group_commands:
            continue
        commands.append(BotCommand(command.name, t(language, f"help.{command.command_key}")))
    return tuple(commands)


async def _sync_botfather_commands(bot: Bot) -> None:
    try:
        for language_code in (None, "en"):
            language = language_code or DEFAULT_LANGUAGE
            await bot.set_my_commands(
                _suggested_bot_commands(language, UserLevel.COMMON, include_group_commands=False),
                scope=BotCommandScopeAllPrivateChats(),
                language_code=language_code,
            )
            await bot.set_my_commands(
                _suggested_bot_commands(language, UserLevel.COMMON, include_group_commands=True),
                scope=BotCommandScopeAllGroupChats(),
                language_code=language_code,
            )
            await bot.set_my_commands(
                _suggested_bot_commands(language, UserLevel.ADMIN, include_group_commands=True),
                scope=BotCommandScopeAllChatAdministrators(),
                language_code=language_code,
            )
            await bot.delete_my_commands(
                scope=BotCommandScopeDefault(),
                language_code=language_code,
            )
    except TelegramError as exc:
        logger.warning("No pude sincronizar los comandos sugeridos de BotFather: %s", exc)


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

    if chat_migration_ids(message) is not None:
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
        try:
            await _maybe_award_daily_galeraza(
                db=state.db,
                message=message,
                user_id=str(user.id),
            )
        except TimedOut as exc:
            timeout_log = (
                "Error manejado al anunciar La Galeraza:\n"
                f"{type(exc).__name__}: {exc}\n"
                "El punto se conservo.\n"
                "Se realizaron 3 intentos totales: el original y 2 reintentos.\n"
                "Telegram no confirmo ninguna respuesta; uno o mas avisos pudieron haberse "
                "enviado igualmente y pueden estar duplicados.\n"
                f"update_id={getattr(update, 'update_id', None)} "
                f"chat_id={message.chat.id} message_id={message.message_id}"
            )
            logger.error(timeout_log, exc_info=True)
            await _send_log_event(
                context.bot,
                state.settings.telegram_log_chat_id,
                timeout_log,
            )
        await _maybe_spawn_hisopo_for_message(
            application=context.application,
            message=message,
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


async def _maybe_spawn_hisopo_for_message(
    application: Application,
    message: Message,
) -> HisopoSpawn | None:
    state = application.bot_data["state"]
    chat_id = str(message.chat.id)
    if message.chat.type not in {"group", "supergroup"}:
        return None
    if not state.db.is_command_group_enabled(chat_id, "hisopos"):
        return None
    intensity_percent = state.db.get_hisopo_intensity_percent(chat_id)
    if not should_spawn_hisopo(intensity_percent, secrets.randbelow(100) + 1):
        return None
    return await _spawn_hisopo(application, chat_id, source="message")


async def _spawn_hisopo(
    application: Application,
    chat_id: str,
    source: str,
    now: datetime | None = None,
) -> HisopoSpawn | None:
    state = application.bot_data["state"]
    selection = select_hisopo_spawn(
        secrets.randbelow(100) + 1,
        randbelow=secrets.randbelow,
    )
    actual_kind = selection.actual
    appearance_kind = selection.appearance
    required_types = {actual_kind.key, appearance_kind.key}
    missing_types = sorted(
        hisopo_type
        for hisopo_type in required_types
        if not _hisopo_file_id(state.settings, hisopo_type)
    )
    if missing_types:
        logger.info(
            "El Hisopo %s aun no tiene todos sus file_id (%s); "
            "uso el Hisopo comun en el chat %s.",
            actual_kind.key,
            ", ".join(missing_types),
            chat_id,
        )
        actual_kind = COMMON_HISOPO
        appearance_kind = COMMON_HISOPO
    file_id = _hisopo_file_id(state.settings, appearance_kind.key)
    if not file_id:
        logger.warning(
            "No pude lanzar un Hisopo en el chat %s: falta configurar el file_id comun.",
            chat_id,
        )
        return None

    language = _chat_language(state.db, chat_id)
    type_label = t(language, f"hisopos.type.{appearance_kind.key}")
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(t(language, "hisopos.capture_button"), callback_data=HISOPO_CAPTURE_CALLBACK)]]
    )
    try:
        caption_key = (
            "hisopos.appeared_mystery"
            if appearance_kind.hides_points
            else "hisopos.appeared"
        )
        message = await application.bot.send_photo(
            chat_id=_parse_chat_id(chat_id),
            photo=file_id,
            caption=t(
                language,
                caption_key,
                type_label=type_label,
                points=appearance_kind.points,
            ),
            reply_markup=keyboard,
        )
    except TelegramError as exc:
        logger.warning("No pude lanzar un Hisopo en el chat %s: %s", chat_id, exc)
        return None

    spawned_at = now or datetime.now(timezone.utc)
    if spawned_at.tzinfo is None:
        spawned_at = spawned_at.replace(tzinfo=timezone.utc)
    spawn = state.db.save_hisopo_spawn(
        chat_id=chat_id,
        message_id=str(message.message_id),
        hisopo_type=actual_kind.key,
        appearance_type=appearance_kind.key,
        points=actual_kind.points,
        source=source,
        spawned_at=spawned_at.isoformat(),
        expires_at=(spawned_at + appearance_kind.expiration).isoformat(),
    )
    _schedule_hisopo_expiration(application, spawn)
    return spawn


def _hisopo_file_id(settings: Settings, hisopo_type: str) -> str | None:
    return {
        "common": settings.telegram_hisopo_common_file_id,
        "silver": settings.telegram_hisopo_silver_file_id,
        "gold": settings.telegram_hisopo_gold_file_id,
        "diamond": settings.telegram_hisopo_diamond_file_id,
        "fleeting": settings.telegram_hisopo_fleeting_file_id,
        "mystery": settings.telegram_hisopo_mystery_file_id,
        "putrid": settings.telegram_hisopo_putrid_file_id,
        "radioactive": settings.telegram_hisopo_radioactive_file_id,
        "fake": settings.telegram_hisopo_fake_file_id,
        "twin": settings.telegram_hisopo_twin_file_id,
    }.get(hisopo_type)


def _restore_hisopo_jobs(application: Application) -> None:
    state = application.bot_data["state"]
    state.db.reset_processing_hisopo_schedules()
    for spawn in state.db.list_active_hisopo_spawns():
        _schedule_hisopo_expiration(application, spawn)
    for schedule in state.db.list_pending_hisopo_schedules():
        _schedule_hisopo_appearance(application, schedule)


def _schedule_hisopo_expiration(application: Application, spawn: HisopoSpawn) -> None:
    application.job_queue.run_once(
        _expire_hisopo_job,
        when=_seconds_until(spawn.expires_at),
        data={"chat_id": spawn.chat_id, "message_id": spawn.message_id},
        name=f"hisopo-expire:{spawn.chat_id}:{spawn.message_id}",
    )


def _schedule_hisopo_appearance(application: Application, schedule: HisopoSchedule) -> None:
    application.job_queue.run_once(
        _scheduled_hisopo_job,
        when=_seconds_until(schedule.scheduled_for),
        data={"schedule_id": schedule.schedule_id},
        name=f"hisopo-scheduled:{schedule.schedule_id}",
    )


def _seconds_until(timestamp: str) -> float:
    target = datetime.fromisoformat(timestamp)
    if target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)
    return max((target - datetime.now(timezone.utc)).total_seconds(), 0.0)


async def _expire_hisopo_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    data = context.job.data
    chat_id = state.db.resolve_chat_id(str(data["chat_id"]))
    message_id = str(data["message_id"])
    if not state.db.mark_hisopo_rotten(chat_id, message_id, datetime.now(timezone.utc)):
        return
    spawn = state.db.get_hisopo_spawn(chat_id, message_id)
    if spawn is not None:
        await _edit_rotten_hisopo(context.bot, state.db, spawn)


async def _scheduled_hisopo_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    schedule = state.db.claim_hisopo_schedule(int(context.job.data["schedule_id"]))
    if schedule is None:
        return
    chat_id = state.db.resolve_chat_id(schedule.chat_id)
    if not state.db.is_command_group_enabled(chat_id, "hisopos"):
        state.db.complete_hisopo_schedule(schedule.schedule_id, "cancelled")
        return
    spawn = await _spawn_hisopo(context.application, chat_id, source="scheduled")
    state.db.complete_hisopo_schedule(
        schedule.schedule_id,
        "sent" if spawn is not None else "failed",
    )


async def _hisopo_callback_entrypoint(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    state = _state(context)
    callback_query = update.callback_query
    user = update.effective_user
    message = callback_query.message if callback_query is not None else None
    if callback_query is None or user is None or message is None:
        return

    language = _chat_language(state.db, message.chat.id)
    state.db.get_or_create_user(str(user.id), _display_name(user), user.username)
    if state.db.is_user_blocked(str(user.id)) or _is_user_restricted_in_callback_chat(
        state.db,
        callback_query,
        str(user.id),
    ):
        await callback_query.answer()
        return
    if callback_query.data != HISOPO_CAPTURE_CALLBACK:
        await callback_query.answer(t(language, "hisopos.unavailable_alert"), show_alert=True)
        return

    now = datetime.now(timezone.utc)
    spawn = state.db.get_hisopo_spawn(str(message.chat.id), str(message.message_id))
    next_scheduled_for = ()
    points_at_capture = None
    expired_mystery_fleeting = False
    if spawn is not None:
        expired_mystery_fleeting = (
            spawn.hisopo_type == "fleeting"
            and spawn.appearance_type == "mystery"
            and is_fleeting_window_expired(
                datetime.fromisoformat(spawn.spawned_at),
                now,
            )
        )
        kind = hisopo_kind_for_spawn(spawn.hisopo_type, spawn.points)
        if not expired_mystery_fleeting:
            next_scheduled_for = tuple(
                random_next_day_datetime(now) for _ in range(kind.next_day_spawns)
            )
        if spawn.hisopo_type == "radioactive":
            points_at_capture = radioactive_points_at(
                datetime.fromisoformat(spawn.spawned_at),
                now,
            )
        elif expired_mystery_fleeting:
            points_at_capture = 0
    result = state.db.capture_hisopo(
        chat_id=str(message.chat.id),
        message_id=str(message.message_id),
        user_id=str(user.id),
        now=now,
        next_scheduled_for=next_scheduled_for,
        points_at_capture=points_at_capture,
    )
    if result.status == "captured" and result.spawn is not None:
        type_label = t(language, f"hisopos.type.{result.spawn.hisopo_type}")
        if expired_mystery_fleeting:
            caption_key = "hisopos.expired_fleeting_caption"
            popup_key = "hisopos.expired_fleeting_popup"
        elif result.spawn.points < 0:
            caption_key = "hisopos.captured_caption_negative"
            popup_key = "hisopos.captured_popup_negative"
        elif result.spawn.points == 0:
            caption_key = "hisopos.captured_caption_zero"
            popup_key = "hisopos.captured_popup_zero"
        else:
            caption_key = "hisopos.captured_caption"
            popup_key = "hisopos.captured_popup"
        await _edit_hisopo_result(
            context.bot,
            state.settings,
            result.spawn,
            t(
                language,
                caption_key,
                user=_display_name(user),
                type_label=type_label,
                points=abs(result.spawn.points),
            ),
        )
        for schedule in result.schedules:
            _schedule_hisopo_appearance(context.application, schedule)
        await callback_query.answer(
            t(language, popup_key, points=abs(result.spawn.points))
        )
        captured_kind = hisopo_kind_for_spawn(
            result.spawn.hisopo_type,
            result.spawn.points,
        )
        for _ in range(captured_kind.immediate_spawns):
            await _spawn_hisopo(
                context.application,
                result.spawn.chat_id,
                source="twin",
            )
        return
    if result.status == "taken":
        await callback_query.answer(t(language, "hisopos.taken_alert"), show_alert=True)
        return
    if result.status == "rotten":
        if result.spawn is not None:
            await _edit_rotten_hisopo(context.bot, state.db, result.spawn)
        await callback_query.answer(t(language, "hisopos.rotten_alert"), show_alert=True)
        return
    await callback_query.answer(t(language, "hisopos.unavailable_alert"), show_alert=True)


async def _edit_rotten_hisopo(bot: Bot, db: Database, spawn: HisopoSpawn) -> None:
    language = _chat_language(db, spawn.chat_id)
    await _edit_hisopo_caption(
        bot,
        spawn,
        t(
            language,
            "hisopos.rotten_caption",
            type_label=t(language, f"hisopos.type.{spawn.appearance_type}"),
        ),
    )


async def _edit_hisopo_result(
    bot: Bot,
    settings: Settings,
    spawn: HisopoSpawn,
    caption: str,
) -> None:
    if spawn.appearance_type != spawn.hisopo_type:
        file_id = _hisopo_file_id(settings, spawn.hisopo_type)
        if file_id:
            try:
                await bot.edit_message_media(
                    chat_id=_parse_chat_id(spawn.chat_id),
                    message_id=int(spawn.message_id),
                    media=InputMediaPhoto(media=file_id, caption=caption),
                    reply_markup=None,
                )
                return
            except TelegramError as exc:
                logger.warning(
                    "No pude revelar la imagen del Hisopo %s en el chat %s: %s",
                    spawn.message_id,
                    spawn.chat_id,
                    exc,
                )
        else:
            logger.warning(
                "No pude revelar la imagen del Hisopo %s en el chat %s: "
                "falta el file_id de %s.",
                spawn.message_id,
                spawn.chat_id,
                spawn.hisopo_type,
            )
    await _edit_hisopo_caption(bot, spawn, caption)


async def _edit_hisopo_caption(bot: Bot, spawn: HisopoSpawn, caption: str) -> None:
    try:
        await bot.edit_message_caption(
            chat_id=_parse_chat_id(spawn.chat_id),
            message_id=int(spawn.message_id),
            caption=caption,
            reply_markup=None,
        )
    except TelegramError as exc:
        logger.warning(
            "No pude quitar la botonera del Hisopo %s en el chat %s: %s",
            spawn.message_id,
            spawn.chat_id,
            exc,
        )


async def _chat_migration_entrypoint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return

    _handle_chat_migration(message, _state(context).db)


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


async def _handle_command_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if message is None or user is None or chat is None or not message.text:
        return

    command = get_command(message.text)
    if command is not None and getattr(command, "command_key", None) in {"reiniciarbot", "apagar"}:
        await _cleanup_expired_restart_confirmations(state.db, context.bot)

    state.db.get_or_create_user(str(user.id), _display_name(user), user.username)
    if state.db.is_user_blocked(str(user.id)):
        return
    if _is_user_restricted_in_message_chat(state.db, message, str(user.id)):
        return

    user_level = UserLevel.COMMON
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
        broadcast_announcement=lambda text: _broadcast_announcement(
            db=state.db,
            bot=context.bot,
            text=text,
            announcements_chat_id=state.settings.telegram_announcements_chat_id,
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
        send_hisopos=lambda: _send_hisopos(state.db, message, str(user.id)),
        send_config_menu=lambda: _send_config_menu(state.db, message),
        create_restart_confirmation=lambda: _create_restart_confirmation(
            state.db,
            message,
            str(user.id),
        ),
        create_shutdown_confirmation=lambda: _create_restart_confirmation(
            state.db,
            message,
            str(user.id),
            shutdown=True,
        ),
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


async def _restart_callback_entrypoint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    callback_query = update.callback_query
    user = update.effective_user
    message = callback_query.message if callback_query is not None else None
    if callback_query is None or user is None or message is None:
        return

    await _cleanup_expired_restart_confirmations(state.db, context.bot)
    confirmation = state.db.get_restart_confirmation(str(message.chat.id), str(message.message_id))
    language = _chat_language(state.db, message.chat.id)
    if confirmation is None:
        await _delete_restart_confirmation_message(state.db, message)
        await callback_query.answer(t(language, "restart.deleted"))
        return
    if str(user.id) != confirmation.requester_user_id:
        await callback_query.answer(t(language, "restart.invalid_user"))
        return

    callback_prefix, _, action = (callback_query.data or "").partition(":")
    await _delete_restart_confirmation_message(state.db, message)
    if action == "no":
        await callback_query.answer(t(language, "restart.cancelled"))
        return
    if action != "yes":
        await callback_query.answer(t(language, "restart.deleted"))
        return

    if callback_prefix == SHUTDOWN_CALLBACK_PREFIX:
        await callback_query.answer(t(language, "shutdown.confirmed"))
        _request_shutdown(context.application)
        return
    await callback_query.answer(t(language, "restart.confirmed"))
    _request_restart(context.application)


async def _config_callback_entrypoint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _state(context)
    callback_query = update.callback_query
    user = update.effective_user
    if callback_query is None or user is None:
        return

    state.db.get_or_create_user(str(user.id), _display_name(user), user.username)
    message = callback_query.message
    language = _chat_language(state.db, message.chat.id) if message is not None else DEFAULT_LANGUAGE
    if message is None or message.chat.type not in {"private", "group", "supergroup"}:
        await callback_query.answer(t(language, "config.unsupported_chat"))
        return

    parsed = parse_config_callback(callback_query.data or "")
    if _is_legacy_expense_config_callback(parsed):
        await message.delete()
        await callback_query.answer(t(language, "pagination.deleted"))
        return

    if state.db.is_user_blocked(str(user.id)):
        await callback_query.answer()
        return
    if _is_user_restricted_in_callback_chat(state.db, callback_query, str(user.id)):
        await callback_query.answer()
        return

    user_level = await _resolve_user_level(
        user_id=str(user.id),
        chat=message.chat,
        db=state.db,
        bot=context.bot,
        dev_user_ids=state.settings.telegram_dev_user_ids,
    )
    if message.chat.type in {"group", "supergroup"} and user_level < UserLevel.ADMIN:
        await callback_query.answer(t(language, "config.permission_popup"))
        return

    if parsed is None:
        await callback_query.answer()
        return

    popup_text = await _handle_config_callback(state.db, message, parsed)
    await callback_query.answer(text=popup_text)


def _is_legacy_expense_config_callback(parsed: tuple[str, ...] | None) -> bool:
    return parsed is not None and len(parsed) >= 2 and parsed[0] in {"command", "set"} and parsed[1] == "gastos"


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
    if (
        update is None
        and isinstance(context.error, NetworkError)
        and getattr(context, "job", None) is None
        and getattr(context, "coroutine", None) is None
    ):
        logger.warning(
            "Error transitorio de red durante polling; python-telegram-bot reintentara: %s",
            context.error,
        )
        return

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

    entities = _bold_first_line_entities(page.text) if list_type == "triggers" else None
    result = await message.reply_text(page.text, do_quote=True, entities=entities)
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
        entities=entities,
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
            reply_markup=build_main_menu(language, _chat_supports_command_groups(message.chat.type)),
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
        await message.edit_text(
            t(language, "config.title"),
            reply_markup=build_main_menu(language, _chat_supports_command_groups(message.chat.type)),
        )
        return None

    if action == "language":
        settings = db.get_chat_settings(chat_id)
        await message.edit_text(t(settings.language, "config.language"), reply_markup=build_language_menu(settings.language))
        return None

    if action == "announcements":
        settings = db.get_chat_settings(chat_id)
        await message.edit_text(
            t(language, "config.announcements"),
            reply_markup=build_announcements_menu(settings.announcements_enabled, language),
        )
        return None

    if action == "setannouncements" and len(parsed) == 2:
        enabled = parsed[1] == "1"
        settings = db.get_chat_settings(chat_id)
        if settings.announcements_enabled == enabled:
            return None
        db.set_chat_announcements_enabled(chat_id, enabled)
        await message.edit_text(
            t(language, "config.announcements"),
            reply_markup=build_announcements_menu(enabled, language),
        )
        return t(language, "config.updated")

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
        if not _chat_supports_command_groups(message.chat.type):
            return None
        await message.edit_text(t(language, "config.commands"), reply_markup=build_command_groups_menu(language))
        return None

    if action == "command" and len(parsed) == 2:
        command_group = parsed[1]
        if not is_valid_command_group(command_group):
            return None
        enabled = db.is_command_group_enabled(chat_id, command_group)
        if command_group == "hisopos":
            intensity_percent = db.get_hisopo_intensity_percent(chat_id)
            await message.edit_text(
                _hisopo_config_text(language),
                reply_markup=build_hisopo_menu(enabled, intensity_percent, language),
            )
            return None
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
        if command_group == "hisopos":
            await message.edit_text(
                _hisopo_config_text(language),
                reply_markup=build_hisopo_menu(
                    enabled,
                    db.get_hisopo_intensity_percent(chat_id),
                    language,
                ),
            )
            return t(language, "config.updated")
        await message.edit_text(
            f"{command_group_label(command_group, language)}\n\n{t(language, 'config.enabled_question')}",
            reply_markup=build_command_group_menu(command_group, enabled, language),
        )
        return t(language, "config.updated")

    if action == "intensity" and len(parsed) == 2:
        try:
            intensity_percent = int(parsed[1])
            current_intensity = db.get_hisopo_intensity_percent(chat_id)
            if current_intensity == intensity_percent:
                return None
            db.set_hisopo_intensity_percent(chat_id, intensity_percent)
        except ValueError:
            return None
        await message.edit_text(
            _hisopo_config_text(language),
            reply_markup=build_hisopo_menu(
                db.is_command_group_enabled(chat_id, "hisopos"),
                intensity_percent,
                language,
            ),
        )
        return t(language, "config.updated")

    return None


def _chat_supports_command_groups(chat_type: str) -> bool:
    return chat_type in {"group", "supergroup"}


def _hisopo_config_text(language: str) -> str:
    return (
        f"{command_group_label('hisopos', language)}\n\n"
        f"{t(language, 'config.enabled_question')}\n\n"
        f"{t(language, 'hisopos.intensity.title')}"
    )


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


async def _create_restart_confirmation(
    db: Database,
    message: Message,
    requester_user_id: str,
    shutdown: bool = False,
) -> bool:
    language = _chat_language(db, message.chat.id)
    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(t(language, "restart.yes"), callback_data=f"{SHUTDOWN_CALLBACK_PREFIX if shutdown else RESTART_CALLBACK_PREFIX}:yes"),
            InlineKeyboardButton(t(language, "restart.no"), callback_data=f"{SHUTDOWN_CALLBACK_PREFIX if shutdown else RESTART_CALLBACK_PREFIX}:no"),
        ]]
    )
    try:
        confirmation_message = await message.reply_text(
            t(language, "shutdown.prompt" if shutdown else "restart.prompt"),
            reply_markup=keyboard,
            do_quote=True,
        )
    except TelegramError:
        logger.warning("No pude crear el tablero de reinicio en chat %s.", message.chat.id)
        return False

    db.save_restart_confirmation(
        chat_id=str(message.chat.id),
        message_id=str(confirmation_message.message_id),
        requester_user_id=requester_user_id,
    )
    return True


async def _delete_restart_confirmation_message(db: Database, message: Message) -> None:
    try:
        await message.delete()
    except TelegramError as exc:
        logger.warning("No pude eliminar tablero de reinicio %s en chat %s: %s", message.message_id, message.chat.id, exc)
    finally:
        db.delete_restart_confirmation(str(message.chat.id), str(message.message_id))


async def _delete_restart_confirmation_by_id(
    db: Database,
    bot: Bot,
    chat_id: int | str,
    message_id: str,
) -> None:
    try:
        await bot.delete_message(chat_id=chat_id, message_id=int(message_id))
    except TelegramError as exc:
        logger.warning("No pude eliminar tablero de reinicio %s en chat %s: %s", message_id, chat_id, exc)
    finally:
        db.delete_restart_confirmation(str(chat_id), message_id)


async def _cleanup_expired_restart_confirmations(db: Database, bot: Bot) -> None:
    cutoff = (datetime.now(timezone.utc) - RESTART_CONFIRMATION_TTL).strftime("%Y-%m-%d %H:%M:%S")
    for confirmation in db.list_restart_confirmations_before(cutoff):
        await _delete_restart_confirmation_by_id(
            db,
            bot,
            _parse_chat_id(confirmation.chat_id),
            confirmation.message_id,
        )


def _request_restart(application: Application) -> None:
    if application.bot_data.get("power_requested"):
        return
    application.bot_data["restart_requested"] = True
    application.bot_data["power_requested"] = "restart"
    application.create_task(_stop_after_pending_updates(application, "restart"), name="restart-after-pending-updates")


def _request_shutdown(application: Application) -> None:
    if application.bot_data.get("power_requested"):
        return
    application.bot_data["power_requested"] = "shutdown"
    application.create_task(_stop_after_pending_updates(application, "shutdown"), name="shutdown-after-pending-updates")


async def _stop_after_pending_updates(application: Application, action: str) -> None:
    await asyncio.sleep(0)
    try:
        await application.updater.stop()
    except RuntimeError:
        logger.info("El Updater ya estaba detenido durante %s.", action)
    try:
        await asyncio.wait_for(application.update_queue.join(), timeout=UPDATE_DRAIN_TIMEOUT_SECONDS)
    except TimeoutError:
        text = f"El drenaje de updates excedio {UPDATE_DRAIN_TIMEOUT_SECONDS} segundos durante {action}."
        logger.error(text)
        await _send_log_event(application.bot, application.bot_data["settings"].telegram_log_chat_id, text)
        if action == "restart":
            _mark_panel_restart_pending()
            os.execv(sys.executable, [sys.executable, *sys.argv])
        os._exit(0)
    application.stop_running()


async def _restart_after_pending_updates(application: Application) -> None:
    await _stop_after_pending_updates(application, "restart")


def _paginated_metadata_cutoff() -> str:
    return (datetime.now(timezone.utc) - PAGINATED_METADATA_TTL).strftime("%Y-%m-%d %H:%M:%S")


def _is_paginated_state_expired(created_at: str) -> bool:
    try:
        created = datetime.fromisoformat(created_at.replace(" ", "T"))
    except ValueError:
        logger.warning("Fecha invalida en metadata de botonera: %s", created_at)
        return False

    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - created > PAGINATED_METADATA_TTL


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
    if state.list_type in {"galeraza", "hisopos"} and "pages" in content:
        rendered = render_prebuilt_pages(content["pages"], page=page)
    else:
        rendered = render_page(content["header"], content["lines"], page=page)
    db.set_paginated_message_page(str(message.chat.id), message_id, rendered.page)
    edit_options = {}
    if state.list_type in {"galeraza", "hisopos", "triggers"}:
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
    migration_ids = chat_migration_ids(message)
    if migration_ids is None:
        return False
    old_chat_id, new_chat_id = migration_ids

    if not db.migrate_chat_id(old_chat_id=str(old_chat_id), new_chat_id=str(new_chat_id)):
        return False
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
            link_preview_options=DISABLED_LINK_PREVIEW_OPTIONS,
        )
        if was_truncated:
            await _send_log_event(bot, log_chat_id, t(language, "long_message.truncated_log"))
    except (TelegramError, ValueError) as exc:
        logger.warning("No pude enviar novedad al canal de anuncios: %s", exc)
        return False

    return True


async def _broadcast_announcement(
    db: Database,
    bot: Bot,
    text: str,
    announcements_chat_id: str | None,
) -> AnnouncementBroadcastResult:
    if not announcement_fits(text, TELEGRAM_MESSAGE_LIMIT_CHARS):
        return AnnouncementBroadcastResult(too_long=True)

    announcement_chat_id = str(announcements_chat_id) if announcements_chat_id else None
    sent_count = 0
    skipped_count = 0
    inactive_count = 0
    failed_count = 0
    for chat in db.list_active_chats():
        if chat.chat_id == announcement_chat_id:
            continue
        settings = db.get_chat_settings(chat.chat_id)
        if not settings.announcements_enabled:
            skipped_count += 1
            continue
        try:
            await bot.send_message(
                chat_id=_parse_chat_id(chat.chat_id),
                text=format_announcement(text, settings.language),
                link_preview_options=DISABLED_LINK_PREVIEW_OPTIONS,
            )
        except TelegramError as exc:
            if _is_bot_removed_error(exc):
                db.mark_chat_inactive(chat.chat_id, "announcement_send_failed")
                inactive_count += 1
            else:
                failed_count += 1
            logger.warning("No pude enviar anuncio al chat %s: %s", chat.chat_id, exc)
            continue
        sent_count += 1

    announcement_channel_sent = False
    if announcement_chat_id:
        channel_language = _chat_language(db, announcement_chat_id)
        try:
            await bot.send_message(
                chat_id=_parse_chat_id(announcement_chat_id),
                text=format_announcement(text, channel_language),
                link_preview_options=DISABLED_LINK_PREVIEW_OPTIONS,
            )
        except (TelegramError, ValueError) as exc:
            logger.warning("No pude enviar anuncio al canal de anuncios: %s", exc)
        else:
            announcement_channel_sent = True

    return AnnouncementBroadcastResult(
        sent_count=sent_count,
        skipped_count=skipped_count,
        inactive_count=inactive_count,
        failed_count=failed_count,
        announcement_channel_sent=announcement_channel_sent,
    )


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

        update_id = update.update_id if isinstance(update, Update) else None
        update_label = str(update_id) if update_id is not None else "sin id"
        filename = f"Debug de la update {update_label}"
        payload = debug_json.encode("utf-8")

        async def send_document() -> None:
            await message.reply_document(
                document=BytesIO(payload),
                filename=filename,
                do_quote=True,
                read_timeout=TELEGRAM_DOCUMENT_TIMEOUT_SECONDS,
                write_timeout=TELEGRAM_DOCUMENT_TIMEOUT_SECONDS,
                connect_timeout=TELEGRAM_DOCUMENT_TIMEOUT_SECONDS,
                pool_timeout=TELEGRAM_DOCUMENT_TIMEOUT_SECONDS,
            )

        try:
            await send_document()
        except TimedOut:
            logger.warning("Timeout al enviar update de debug; reintentando una vez.")
            await send_document()
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
