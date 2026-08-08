from __future__ import annotations

from ..command_model import Command
from ..database import Database
from ..roles import CommandContext


def handle(context: CommandContext, db: Database) -> str:
    user = db.get_or_create_user(context.sender_id)
    name = user.display_name or "galerazo"
    return context.t("hola.response", name=name)


COMMANDS = {
    "hola": Command("hola", "saluda al bot", handle),
}
