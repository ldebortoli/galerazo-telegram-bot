from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext


def handle(context: CommandContext, _db: Database) -> str:
    return f"Tu nivel es: {context.user_level.label}."


COMMANDS = {
    "nivel": Command("nivel", "muestra tu nivel de usuario", handle),
}
