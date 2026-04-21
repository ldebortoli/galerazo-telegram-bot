from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext


def handle(context: CommandContext, _db: Database) -> str:
    from ..commands import iter_commands

    lines = [context.t("help.header")]
    for command in iter_commands():
        if command.hidden or context.user_level < command.min_level:
            continue
        if (
            context.chat_id is not None
            and context.chat_type in {"group", "supergroup"}
            and command.configurable_group is not None
            and not _db.is_command_group_enabled(context.chat_id, command.configurable_group)
        ):
            continue
        lines.append(f"- {command.name}: {context.t(f'help.{command.command_key}')}")
    return "\n".join(lines)


COMMANDS = {
    "help": Command("help / ayuda", "muestra esta ayuda", handle, list_response=True),
    "ayuda": Command("ayuda", "muestra esta ayuda", handle, hidden=True, list_response=True),
}
