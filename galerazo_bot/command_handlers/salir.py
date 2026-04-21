from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext, UserLevel


async def handle(context: CommandContext, _db: Database) -> str:
    if context.chat_type not in {"group", "supergroup"}:
        return context.t("salir.group_only")

    if context.reply_to_user_id is None:
        return context.t("salir.usage")

    if context.reply_to_user_id != context.bot_user_id:
        return context.t("salir.usage")

    if context.leave_chat is None:
        return context.t("salir.not_configured")

    if not await context.leave_chat():
        return context.t("salir.failed")

    return context.t("salir.leaving")


COMMANDS = {
    "salir": Command(
        "salir",
        "hace que el bot salga del grupo",
        handle,
        UserLevel.DEV,
        permission_error_key="salir.permission",
    ),
}
