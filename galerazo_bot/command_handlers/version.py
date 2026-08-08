from __future__ import annotations

from ..command_model import Command
from ..database import Database
from ..roles import CommandContext
from ..versioning import CURRENT_VERSION


def handle(context: CommandContext, _db: Database) -> str:
    return context.t("version.response", version=CURRENT_VERSION)


COMMANDS = {
    "version": Command("version", "muestra la version actual del bot", handle),
}
