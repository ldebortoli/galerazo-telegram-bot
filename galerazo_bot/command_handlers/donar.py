from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext


def handle(context: CommandContext, _db: Database) -> str:
    return context.t("donation.text")


COMMANDS = {"donar": Command("donar", "muestra como apoyar al bot", handle)}
