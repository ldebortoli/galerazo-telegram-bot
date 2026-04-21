from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional, Union

from .database import Database
from .roles import CommandContext, UserLevel


CommandResult = Union[Optional[str], Awaitable[Optional[str]]]
CommandHandler = Callable[[CommandContext, Database], CommandResult]
DEFAULT_PERMISSION_ERROR = "No tenes permisos suficientes para usar este comando."


@dataclass(frozen=True)
class Command:
    name: str
    description: str
    handler: CommandHandler
    min_level: UserLevel = UserLevel.COMMON
    permission_error: str | None = None
    hidden: bool = False


def normalize_command(text: str) -> str:
    command = text.strip().lower()
    if command.startswith(("!", "/")):
        command = command[1:]
    command_name = command.split(maxsplit=1)[0] if command else ""
    return command_name.split("@", maxsplit=1)[0]


def command_args(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""

    parts = stripped.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


def is_command_invocation(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False

    return stripped.startswith(("!", "/")) or normalize_command(stripped) in COMMANDS


def command_exists(text: str) -> bool:
    return normalize_command(text) in COMMANDS


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
        )
    )


async def handle_text_async(
    text: str,
    sender_id: str,
    db: Database,
    chat_id: str | None = None,
    user_level: UserLevel = UserLevel.COMMON,
) -> str | None:
    context = CommandContext(
        sender_id=sender_id,
        chat_id=chat_id,
        chat_type=None,
        user_level=user_level,
        raw_text=text,
        args=command_args(text),
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
    chat_type: str | None = None,
    bot_user_id: str | None = None,
    send_announcement=None,
    create_backup=None,
    send_debug_update=None,
    send_galerazas=None,
    leave_chat=None,
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
            chat_type=chat_type,
            bot_user_id=bot_user_id,
            send_announcement=send_announcement,
            create_backup=create_backup,
            send_debug_update=send_debug_update,
            send_galerazas=send_galerazas,
            leave_chat=leave_chat,
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
    chat_type: str | None = None,
    bot_user_id: str | None = None,
    send_announcement=None,
    create_backup=None,
    send_debug_update=None,
    send_galerazas=None,
    leave_chat=None,
) -> str | None:
    context = CommandContext(
        sender_id=sender_id,
        chat_id=chat_id,
        chat_type=chat_type,
        user_level=user_level,
        raw_text=text,
        args=command_args(text),
        bot_user_id=bot_user_id,
        send_announcement=send_announcement,
        create_backup=create_backup,
        send_debug_update=send_debug_update,
        send_galerazas=send_galerazas,
        leave_chat=leave_chat,
        reply_to_user_id=reply_to_user_id,
        reply_to_username=reply_to_username,
        reply_to_display_name=reply_to_display_name,
    )
    db.save_incoming_message(sender_id=sender_id, text=text, chat_id=chat_id)
    return await _handle_with_context(context, db)


async def _handle_with_context(context: CommandContext, db: Database) -> str | None:
    command_name = normalize_command(context.raw_text)
    command = COMMANDS.get(command_name)
    if command is None:
        return "No conozco ese comando. Escribi help para ver las opciones."

    if context.user_level < command.min_level:
        return command.permission_error or DEFAULT_PERMISSION_ERROR

    result = command.handler(context, db)
    if inspect.isawaitable(result):
        return await result
    return result


def _load_commands() -> dict[str, Command]:
    from .command_handlers import COMMANDS as handler_commands

    return dict(handler_commands)


COMMANDS: dict[str, Command] = _load_commands()
