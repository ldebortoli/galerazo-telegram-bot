from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext, UserLevel


def handle(context: CommandContext, _db: Database) -> str:
    message = context.args.strip()
    if not message:
        return "Uso: /novedad mensaje"

    if context.send_announcement is None:
        return "No hay canal de anuncios configurado."

    if not context.send_announcement(message):
        return "No pude enviar la novedad al canal de anuncios."

    return "Novedad enviada."


COMMANDS = {
    "novedad": Command("novedad", "envia una novedad al canal de anuncios", handle, UserLevel.DEV),
}
