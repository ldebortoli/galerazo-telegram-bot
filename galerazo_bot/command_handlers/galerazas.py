from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext


async def handle(context: CommandContext, _db: Database) -> str | None:
    if context.chat_type not in {"group", "supergroup"}:
        return context.t("galeraza.group_only")

    if context.send_galerazas is None:
        return context.t("galeraza.not_configured")

    if not await context.send_galerazas():
        return context.t("galeraza.send_failed")

    return None


COMMANDS = {
    "galerazas": Command(
        "galerazas",
        "muestra el ranking de la Galeraza",
        handle,
        configurable_group="galeraza",
    ),
    "galeraza": Command(
        "galeraza",
        "muestra el ranking de la Galeraza",
        handle,
        command_key="galerazas",
        configurable_group="galeraza",
    ),
}
