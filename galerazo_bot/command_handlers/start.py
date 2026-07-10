from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext


def handle(context: CommandContext, db: Database) -> str:
    user = db.get_or_create_user(context.sender_id)
    name = user.display_name or "galerazo"
    return context.t("start.response", name=name)


COMMANDS = {
    "start": Command("start", "inicia el bot y muestra como ver la ayuda", handle),
}
