from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext, UserLevel


async def handle(context: CommandContext, _db: Database) -> str | None:
    if context.chat_type not in {"private", "group", "supergroup"}:
        return context.t("config.unsupported_chat")
    if context.chat_type in {"group", "supergroup"} and context.user_level < UserLevel.ADMIN:
        return context.t("permission_denied")

    if context.send_config_menu is None:
        return context.t("config.not_configured")

    if not await context.send_config_menu():
        return context.t("config.send_failed")

    return None


COMMANDS = {
    "config": Command("config", "muestra la configuracion del chat", handle),
}
