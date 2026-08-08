from __future__ import annotations

from ..command_model import Command
from ..database import Database
from ..roles import CommandContext, UserLevel


async def handle(context: CommandContext, _db: Database) -> str | None:
    if context.create_shutdown_confirmation is None:
        return context.t("shutdown.not_configured")
    if not await context.create_shutdown_confirmation():
        return context.t("shutdown.send_failed")
    return None


COMMANDS = {
    "apagar": Command("apagar", "solicita apagar el bot", handle, UserLevel.DEV),
}
