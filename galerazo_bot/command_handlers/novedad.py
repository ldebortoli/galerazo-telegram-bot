from __future__ import annotations

from ..command_model import Command
from ..database import Database
from ..roles import CommandContext, UserLevel


async def handle(context: CommandContext, _db: Database) -> str:
    message = context.args.strip()
    if not message:
        return context.t("novedad.usage")

    if context.send_announcement is None:
        return context.t("novedad.not_configured")

    if not await context.send_announcement(message):
        return context.t("novedad.send_failed")

    return context.t("novedad.sent")


COMMANDS = {
    "novedad": Command("novedad", "envia una novedad al canal de anuncios", handle, UserLevel.DEV),
}
