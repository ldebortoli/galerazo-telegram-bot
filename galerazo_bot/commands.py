from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional, Union

from .database import Database
from .i18n import DEFAULT_LANGUAGE, t
from .roles import CommandContext, UserLevel


CommandResult = Union[Optional[str], Awaitable[Optional[str]]]
CommandHandler = Callable[[CommandContext, Database], CommandResult]
DEFAULT_PERMISSION_ERROR_KEY = "permission_denied"
SYMBOL_COMMAND_PREFIXES = ("!", "/", ".", ">", "$")


@dataclass(frozen=True)
class Command:
    name: str
    description: str
    handler: CommandHandler
    min_level: UserLevel = UserLevel.COMMON
    permission_error: str | None = None
    permission_error_key: str | None = None
    hidden: bool = False
    configurable_group: str | None = None
    command_key: str | None = None
    list_response: bool = False

    def __post_init__(self) -> None:
        if self.command_key is None:
            object.__setattr__(self, "command_key", self.name.split(maxsplit=1)[0])


def normalize_command(text: str) -> str:
    command, _prefix = _strip_command_prefix(text)
    command = command.lower()
    command_name = command.split(maxsplit=1)[0] if command else ""
    return command_name.split("@", maxsplit=1)[0]


def command_args(text: str) -> str:
    stripped, _prefix = _strip_command_prefix(text)
    if not stripped:
        return ""

    parts = stripped.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


def is_command_invocation(text: str) -> bool:
    stripped, prefix = _strip_command_prefix(text)
    return prefix is not None and bool(stripped)


def _strip_command_prefix(text: str) -> tuple[str, str | None]:
    stripped = text.strip()
    if not stripped:
        return "", None
    if stripped.startswith(SYMBOL_COMMAND_PREFIXES):
        return stripped[1:].lstrip(), stripped[0]

    return stripped, None


def command_exists(text: str) -> bool:
    return is_command_invocation(text) and normalize_command(text) in COMMANDS


def get_command(text: str) -> Command | None:
    if not is_command_invocation(text):
        return None
    return COMMANDS.get(normalize_command(text))


def iter_commands() -> tuple[Command, ...]:
    return tuple(COMMANDS.values())


def handle_text(
    text: str,
    sender_id: str,
    db: Database,
    chat_id: str | None = None,
    user_level: UserLevel = UserLevel.COMMON,
) -> str | None:
    return asyncio.run(
        handle_text_async(
            text=text,
            sender_id=sender_id,
            db=db,
            chat_id=chat_id,
            user_level=user_level,
            language=DEFAULT_LANGUAGE,
        )
    )


async def handle_text_async(
    text: str,
    sender_id: str,
    db: Database,
    chat_id: str | None = None,
    user_level: UserLevel = UserLevel.COMMON,
    language: str = DEFAULT_LANGUAGE,
) -> str | None:
    context = CommandContext(
        sender_id=sender_id,
        chat_id=chat_id,
        chat_type=None,
        user_level=user_level,
        raw_text=text,
        args=command_args(text),
        language=language,
    )
    db.save_incoming_message(sender_id=sender_id, text=text, chat_id=chat_id)
    return await _handle_with_context(context, db)


def handle_command(
    text: str,
    sender_id: str,
    db: Database,
    chat_id: str | None = None,
    user_level: UserLevel = UserLevel.COMMON,
    reply_to_user_id: str | None = None,
    reply_to_username: str | None = None,
    reply_to_display_name: str | None = None,
    reply_to_trigger_payload=None,
    chat_type: str | None = None,
    bot_user_id: str | None = None,
    sender_username: str | None = None,
    sender_display_name: str | None = None,
    send_announcement=None,
    broadcast_announcement=None,
    send_report=None,
    submit_expense=None,
    sync_expenses=None,
    get_expense_sheet_status=None,
    create_backup=None,
    send_debug_update=None,
    send_galerazas=None,
    send_config_menu=None,
    create_restart_confirmation=None,
    create_shutdown_confirmation=None,
    leave_chat=None,
    can_run_russian_roulette=None,
    resolve_russian_roulette_hit=None,
    moderate_trigger_payload=None,
    language: str | None = None,
) -> str | None:
    return asyncio.run(
        handle_command_async(
            text=text,
            sender_id=sender_id,
            db=db,
            chat_id=chat_id,
            user_level=user_level,
            reply_to_user_id=reply_to_user_id,
            reply_to_username=reply_to_username,
            reply_to_display_name=reply_to_display_name,
            reply_to_trigger_payload=reply_to_trigger_payload,
            chat_type=chat_type,
            bot_user_id=bot_user_id,
            sender_username=sender_username,
            sender_display_name=sender_display_name,
            send_announcement=send_announcement,
            broadcast_announcement=broadcast_announcement,
            send_report=send_report,
            submit_expense=submit_expense,
            sync_expenses=sync_expenses,
            get_expense_sheet_status=get_expense_sheet_status,
            create_backup=create_backup,
            send_debug_update=send_debug_update,
            send_galerazas=send_galerazas,
            send_config_menu=send_config_menu,
            create_restart_confirmation=create_restart_confirmation,
            create_shutdown_confirmation=create_shutdown_confirmation,
            leave_chat=leave_chat,
            can_run_russian_roulette=can_run_russian_roulette,
            resolve_russian_roulette_hit=resolve_russian_roulette_hit,
            moderate_trigger_payload=moderate_trigger_payload,
            language=language,
        )
    )


async def handle_command_async(
    text: str,
    sender_id: str,
    db: Database,
    chat_id: str | None = None,
    user_level: UserLevel = UserLevel.COMMON,
    reply_to_user_id: str | None = None,
    reply_to_username: str | None = None,
    reply_to_display_name: str | None = None,
    reply_to_trigger_payload=None,
    chat_type: str | None = None,
    bot_user_id: str | None = None,
    sender_username: str | None = None,
    sender_display_name: str | None = None,
    send_announcement=None,
    broadcast_announcement=None,
    send_report=None,
    submit_expense=None,
    sync_expenses=None,
    get_expense_sheet_status=None,
    create_backup=None,
    send_debug_update=None,
    send_galerazas=None,
    send_config_menu=None,
    create_restart_confirmation=None,
    create_shutdown_confirmation=None,
    leave_chat=None,
    can_run_russian_roulette=None,
    resolve_russian_roulette_hit=None,
    moderate_trigger_payload=None,
    language: str | None = None,
) -> str | None:
    context = CommandContext(
        sender_id=sender_id,
        chat_id=chat_id,
        chat_type=chat_type,
        user_level=user_level,
        raw_text=text,
        args=command_args(text),
        language=language or _resolve_language(db, chat_id, chat_type),
        bot_user_id=bot_user_id,
        sender_username=sender_username,
        sender_display_name=sender_display_name,
        send_announcement=send_announcement,
        broadcast_announcement=broadcast_announcement,
        send_report=send_report,
        submit_expense=submit_expense,
        sync_expenses=sync_expenses,
        get_expense_sheet_status=get_expense_sheet_status,
        create_backup=create_backup,
        send_debug_update=send_debug_update,
        send_galerazas=send_galerazas,
        send_config_menu=send_config_menu,
        create_restart_confirmation=create_restart_confirmation,
        create_shutdown_confirmation=create_shutdown_confirmation,
        leave_chat=leave_chat,
        can_run_russian_roulette=can_run_russian_roulette,
        resolve_russian_roulette_hit=resolve_russian_roulette_hit,
        moderate_trigger_payload=moderate_trigger_payload,
        reply_to_user_id=reply_to_user_id,
        reply_to_username=reply_to_username,
        reply_to_display_name=reply_to_display_name,
        reply_to_trigger_payload=reply_to_trigger_payload,
    )
    db.save_incoming_message(sender_id=sender_id, text=text, chat_id=chat_id)
    return await _handle_with_context(context, db)


async def _handle_with_context(context: CommandContext, db: Database) -> str | None:
    if not is_command_invocation(context.raw_text):
        return None

    command_name = normalize_command(context.raw_text)
    command = COMMANDS.get(command_name)
    if command is None:
        return None

    if context.user_level < command.min_level:
        if command.permission_error_key:
            return context.t(command.permission_error_key)
        if command.permission_error:
            return command.permission_error
        return context.t(DEFAULT_PERMISSION_ERROR_KEY)

    result = command.handler(context, db)
    if inspect.isawaitable(result):
        return await result
    return result


def _load_commands() -> dict[str, Command]:
    from .command_handlers import COMMANDS as handler_commands

    return dict(handler_commands)


def _resolve_language(db: Database, chat_id: str | None, chat_type: str | None) -> str:
    if chat_id is None or chat_type not in {"group", "supergroup"}:
        return DEFAULT_LANGUAGE
    return db.get_chat_settings(chat_id).language


COMMANDS: dict[str, Command] = _load_commands()
