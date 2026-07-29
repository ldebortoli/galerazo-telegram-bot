from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext, UserLevel


async def handle(context: CommandContext, _db: Database) -> str | None:
    if context.create_restart_confirmation is None:
        return context.t("restart.not_configured")
    if not await context.create_restart_confirmation():
        return context.t("restart.send_failed")
    return None


COMMANDS = {
    "reiniciarbot": Command("reiniciarbot", "solicita reiniciar el bot", handle, UserLevel.DEV),
}
