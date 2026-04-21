from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext, UserLevel


async def handle(context: CommandContext, _db: Database) -> str | None:
    if context.send_debug_update is None:
        return context.t("debug.not_configured")

    if not await context.send_debug_update():
        return context.t("debug.send_failed")

    return None


COMMANDS = {
    "debug": Command("debug", "devuelve el update crudo del mensaje", handle, UserLevel.DEV),
}
