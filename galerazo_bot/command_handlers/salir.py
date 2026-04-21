from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext, UserLevel


async def handle(context: CommandContext, _db: Database) -> str:
    if context.chat_type not in {"group", "supergroup"}:
        return "El comando /salir solo funciona en grupos o supergrupos."

    if context.reply_to_user_id is None:
        return "Uso: responde a un mensaje del bot con /salir para que salga del grupo."

    if context.reply_to_user_id != context.bot_user_id:
        return "Uso: responde a un mensaje del bot con /salir para que salga del grupo."

    if context.leave_chat is None:
        return "No hay mecanismo configurado para salir del chat."

    if not await context.leave_chat():
        return "No pude salir del chat."

    return "Saliendo del grupo."


COMMANDS = {
    "salir": Command(
        "salir",
        "hace que el bot salga del grupo",
        handle,
        UserLevel.DEV,
        "No tenes permisos para usar /salir.",
    ),
}
