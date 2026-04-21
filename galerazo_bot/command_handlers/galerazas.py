from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext


async def handle(context: CommandContext, _db: Database) -> str | None:
    if context.chat_type not in {"group", "supergroup"}:
        return "La Galeraza solo funciona en grupos y supergrupos."

    if context.send_galerazas is None:
        return "No hay mecanismo configurado para mostrar la Galeraza."

    if not await context.send_galerazas():
        return "No pude mostrar la Galeraza."

    return None


COMMANDS = {
    "galerazas": Command(
        "galerazas",
        "muestra el ranking de la Galeraza",
        handle,
        configurable_group="galeraza",
    ),
}
