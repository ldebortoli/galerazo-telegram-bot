from __future__ import annotations

from ..command_model import Command
from ..database import Database
from ..roles import CommandContext, UserLevel


HELP_GROUPS = (
    ("general", {"help", "ayuda", "start", "hola", "lil", "nivel", "version", "chats", "debug", "reportar", "donar", "donantes", "paysupport", "terminos"}),
    ("blocking", {"bloquear", "desbloquear", "desloquear", "listanegra", "bloqueados"}),
    ("chat_admin", {"config", "restringir", "habilitar", "restringidos", "salir"}),
    ("galeraza", {"galeraza", "galerazas"}),
    ("triggers", {"agregartrigger", "agrtrigger", "borrartrigger", "eliminartrigger", "eltrigger", "triggers"}),
    ("games", {"hisopos", "coleccionhisopos", "reglashisopo", "ruletarusa"}),
    ("expenses", {"gasto", "pagoresumen", "cierre", "ayudagastos", "ultimosgastos", "estadogastos", "sincronizargastos"}),
    ("dev", {"anuncio", "novedad", "backup", "reiniciarbot", "apagar"}),
)
EXPENSE_COMMAND_KEYS = frozenset(
    {"gasto", "pagoresumen", "cierre", "ayudagastos", "ultimosgastos", "estadogastos", "sincronizargastos"}
)


def handle(context: CommandContext, _db: Database) -> str:
    from ..commands import iter_commands

    available = []
    for command in iter_commands():
        if command.hidden or context.user_level < command.min_level:
            continue
        if command.min_level == UserLevel.DEV and context.chat_type != "private":
            continue
        if command.command_key in EXPENSE_COMMAND_KEYS and not _can_show_expenses(context):
            continue
        available.append(command)

    lines = [context.t("help.header")]
    rendered_names: set[str] = set()
    for group_key, command_keys in HELP_GROUPS:
        group_commands = [command for command in available if command.command_key in command_keys]
        if not group_commands:
            continue
        lines.extend(("", context.t(f"help.group.{group_key}")))
        for command in group_commands:
            rendered_names.add(command.name)
            lines.append(f"/{command.name}: {context.t(f'help.{command.command_key}')}")

    remaining = [command for command in available if command.name not in rendered_names]
    if remaining:
        lines.extend(("", context.t("help.group.other")))
        lines.extend(f"/{command.name}: {context.t(f'help.{command.command_key}')}" for command in remaining)

    if context.user_level >= UserLevel.DEV and context.chat_type != "private":
        lines.extend(("", context.t("help.dev_private_hint")))
    return "\n".join(lines)


def _can_show_expenses(context: CommandContext) -> bool:
    return context.chat_type == "private" and context.sender_id in context.expense_user_ids


COMMANDS = {
    "help": Command("help", "muestra esta ayuda", handle, list_response=True),
    "ayuda": Command("ayuda", "muestra esta ayuda", handle, command_key="help", list_response=True),
}
