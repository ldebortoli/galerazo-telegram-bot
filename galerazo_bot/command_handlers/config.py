from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext, UserLevel


async def handle(context: CommandContext, _db: Database) -> str | None:
    if context.chat_type not in {"group", "supergroup"}:
        return context.t("config.group_only")

    if context.send_config_menu is None:
        return context.t("config.not_configured")

    if not await context.send_config_menu():
        return context.t("config.send_failed")

    return None


COMMANDS = {
    "config": Command("config", "muestra la configuracion del grupo", handle, UserLevel.ADMIN),
}
