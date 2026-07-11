from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext


def handle(_context: CommandContext, _db: Database) -> str:
    return "LIL"


COMMANDS = {
    "lil": Command("lil", "responde LIL", handle),
}
