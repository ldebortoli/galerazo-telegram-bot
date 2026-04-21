from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext, UserLevel


async def handle(context: CommandContext, _db: Database) -> str | None:
    if context.chat_type not in {"group", "supergroup"}:
        return "El comando /config solo funciona en grupos y supergrupos."

    if context.send_config_menu is None:
        return "No hay mecanismo configurado para mostrar configuracion."

    if not await context.send_config_menu():
        return "No pude mostrar la configuracion."

    return None


COMMANDS = {
    "config": Command("config", "muestra la configuracion del grupo", handle, UserLevel.ADMIN),
}
