from __future__ import annotations

from ..command_model import Command
from ..database import Database
from ..roles import CommandContext


def handle(context: CommandContext, _db: Database) -> str:
    return context.t("nivel.response", level=context.user_level.label)


COMMANDS = {
    "nivel": Command("nivel", "muestra tu nivel de usuario", handle),
}
