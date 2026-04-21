from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext


def handle(context: CommandContext, _db: Database) -> str:
    from ..commands import iter_commands

    lines = ["Comandos disponibles:"]
    for command in iter_commands():
        if command.hidden or context.user_level < command.min_level:
            continue
        lines.append(f"- {command.name}: {command.description}")
    return "\n".join(lines)


COMMANDS = {
    "help": Command("help / ayuda", "muestra esta ayuda", handle),
    "ayuda": Command("ayuda", "muestra esta ayuda", handle, hidden=True),
}
