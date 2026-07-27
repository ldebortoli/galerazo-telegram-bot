from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext, UserLevel


async def handle(context: CommandContext, _db: Database) -> str:
    message = context.args.strip()
    if not message:
        return context.t("announcement.usage")
    if context.broadcast_announcement is None:
        return context.t("announcement.not_configured")

    result = await context.broadcast_announcement(message)
    if result.too_long:
        return context.t("announcement.too_long")
    return context.t(
        "announcement.sent",
        sent=result.sent_count,
        skipped=result.skipped_count,
        inactive=result.inactive_count,
        failed=result.failed_count,
        channel="si" if result.announcement_channel_sent else "no",
    )


COMMANDS = {
    "anuncio": Command("anuncio", "envia un anuncio a todos los chats activos", handle, UserLevel.DEV),
}
