from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .database import Database
from .roles import CommandContext, UserLevel


CommandHandler = Callable[[CommandContext, Database], Optional[str]]
DEFAULT_PERMISSION_ERROR = "No tenes permisos suficientes para usar este comando."


@dataclass(frozen=True)
class Command:
    name: str
    description: str
    handler: CommandHandler
    min_level: UserLevel = UserLevel.COMMON
    permission_error: str | None = None


def normalize_command(text: str) -> str:
    command = text.strip().lower()
    if command.startswith(("!", "/")):
        command = command[1:]
    command_name = command.split(maxsplit=1)[0] if command else ""
    return command_name.split("@", maxsplit=1)[0]


def command_args(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""

    parts = stripped.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


def is_command_invocation(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False

    return stripped.startswith(("!", "/")) or normalize_command(stripped) in COMMANDS


def command_exists(text: str) -> bool:
    return normalize_command(text) in COMMANDS


def _help(_context: CommandContext, _db: Database) -> str:
    lines = ["Comandos disponibles:"]
    for command in COMMANDS.values():
        lines.append(f"- {command.name}: {command.description}")
    return "\n".join(lines)


def _hola(context: CommandContext, db: Database) -> str:
    user = db.get_or_create_user(context.sender_id)
    name = user.display_name or "galerazo"
    return f"Hola, {name}. Soy Galerazo Bot."


def _nivel(context: CommandContext, _db: Database) -> str:
    return f"Tu nivel es: {context.user_level.label}."


def _bloquear(context: CommandContext, db: Database) -> str:
    target = _resolve_target_user(context, db)
    if target is None:
        return "Uso: /bloquear respondiendo un mensaje, con @alias o con user id."

    if target.user_id == context.sender_id:
        return "No podes bloquearte a vos mismo."

    db.block_user(user_id=target.user_id, blocked_by_user_id=context.sender_id)
    return f"Usuario bloqueado: {_format_user(target)}."


def _desbloquear(context: CommandContext, db: Database) -> str:
    target = _resolve_target_user(context, db)
    if target is None:
        return "Uso: /desbloquear respondiendo un mensaje, con @alias o con user id."

    was_blocked = db.unblock_user(target.user_id)
    if not was_blocked:
        return f"El usuario no estaba bloqueado: {_format_user(target)}."

    return f"Usuario desbloqueado: {_format_user(target)}."


def _listanegra(_context: CommandContext, db: Database) -> str:
    blocked_users = db.list_blocked_users()
    if not blocked_users:
        return "La lista negra esta vacia."

    lines = ["Usuarios bloqueados:"]
    for user in blocked_users:
        username = f"@{user.username}" if user.username else "sin alias"
        display_name = f" - {user.display_name}" if user.display_name else ""
        lines.append(f"- {user.user_id} ({username}){display_name}")
    return "\n".join(lines)


def _novedad(context: CommandContext, _db: Database) -> str:
    message = context.args.strip()
    if not message:
        return "Uso: /novedad mensaje"

    if context.send_announcement is None:
        return "No hay canal de anuncios configurado."

    if not context.send_announcement(message):
        return "No pude enviar la novedad al canal de anuncios."

    return "Novedad enviada."


def _backup(context: CommandContext, _db: Database) -> str | None:
    if context.create_backup is None:
        return "No hay mecanismo de backup configurado."

    result = context.create_backup()
    if result.sent:
        return None

    size_mb = result.size_bytes / 1024 / 1024
    limit_mb = result.max_size_bytes / 1024 / 1024
    return (
        "El backup no entra en el limite de Telegram "
        f"({size_mb:.2f} MB de {limit_mb:.0f} MB). "
        f"Deje un backup local en: {result.path}"
    )


def _debug(context: CommandContext, _db: Database) -> str | None:
    if context.send_debug_update is None:
        return "No hay mecanismo de debug configurado."

    if not context.send_debug_update():
        return "No pude enviar el update de debug."

    return None


def _chats(_context: CommandContext, db: Database) -> str:
    stats_by_type = {row.chat_type: row for row in db.get_chat_stats()}
    types = {
        "private": "chats privados",
        "group": "grupos",
        "supergroup": "supergrupos",
        "channel": "canales",
    }
    totals = _sum_chat_stats(stats_by_type.values())

    lines = [
        "Estadisticas de chats:",
        f"- Total de chats: {totals['total']}",
        f"- Activos/no eliminados: {totals['active']}",
        f"- Eliminados, bloqueados o expulsados: {totals['inactive']}",
        "",
        "Por tipo:",
    ]

    for chat_type, label in types.items():
        row = stats_by_type.get(chat_type)
        total = row.total if row else 0
        active = row.active if row else 0
        inactive = row.inactive if row else 0
        lines.append(f"- {label}: total {total}, activos {active}, inactivos {inactive}")

    return "\n".join(lines)


def _salir(context: CommandContext, _db: Database) -> str:
    if context.chat_type not in {"group", "supergroup"}:
        return "El comando /salir solo funciona en grupos o supergrupos."

    if context.reply_to_user_id is None:
        return "Uso: responde a un mensaje del bot con /salir para que salga del grupo."

    if context.reply_to_user_id != context.bot_user_id:
        return "Uso: responde a un mensaje del bot con /salir para que salga del grupo."

    if context.leave_chat is None:
        return "No hay mecanismo configurado para salir del chat."

    if not context.leave_chat():
        return "No pude salir del chat."

    return "Saliendo del grupo."


COMMANDS: dict[str, Command] = {
    "help": Command("help", "muestra esta ayuda", _help),
    "hola": Command("hola", "saluda al bot", _hola),
    "nivel": Command("nivel", "muestra tu nivel de usuario", _nivel),
    "bloquear": Command("bloquear", "bloquea un usuario", _bloquear, UserLevel.DEV),
    "desbloquear": Command("desbloquear", "desbloquea un usuario", _desbloquear, UserLevel.DEV),
    "desloquear": Command("desloquear", "desbloquea un usuario", _desbloquear, UserLevel.DEV),
    "listanegra": Command("listanegra", "muestra usuarios bloqueados", _listanegra, UserLevel.DEV),
    "novedad": Command("novedad", "envia una novedad al canal de anuncios", _novedad, UserLevel.DEV),
    "backup": Command("backup", "envia un backup de la base de datos", _backup, UserLevel.DEV),
    "debug": Command("debug", "devuelve el update crudo del mensaje", _debug, UserLevel.DEV),
    "chats": Command("chats", "muestra estadisticas de chats", _chats),
    "salir": Command(
        "salir",
        "hace que el bot salga del grupo",
        _salir,
        UserLevel.DEV,
        "No tenes permisos para usar /salir.",
    ),
}


def handle_text(
    text: str,
    sender_id: str,
    db: Database,
    chat_id: str | None = None,
    user_level: UserLevel = UserLevel.COMMON,
) -> str | None:
    context = CommandContext(
        sender_id=sender_id,
        chat_id=chat_id,
        chat_type=None,
        user_level=user_level,
        raw_text=text,
        args=command_args(text),
    )
    db.save_incoming_message(sender_id=sender_id, text=text, chat_id=chat_id)

    command_name = normalize_command(text)
    command = COMMANDS.get(command_name)
    if command is None:
        return "No conozco ese comando. Escribi help para ver las opciones."

    if context.user_level < command.min_level:
        return command.permission_error or DEFAULT_PERMISSION_ERROR

    return command.handler(context, db)


def handle_command(
    text: str,
    sender_id: str,
    db: Database,
    chat_id: str | None = None,
    user_level: UserLevel = UserLevel.COMMON,
    reply_to_user_id: str | None = None,
    reply_to_username: str | None = None,
    reply_to_display_name: str | None = None,
    chat_type: str | None = None,
    bot_user_id: str | None = None,
    send_announcement=None,
    create_backup=None,
    send_debug_update=None,
    leave_chat=None,
) -> str | None:
    context = CommandContext(
        sender_id=sender_id,
        chat_id=chat_id,
        chat_type=chat_type,
        user_level=user_level,
        raw_text=text,
        args=command_args(text),
        bot_user_id=bot_user_id,
        send_announcement=send_announcement,
        create_backup=create_backup,
        send_debug_update=send_debug_update,
        leave_chat=leave_chat,
        reply_to_user_id=reply_to_user_id,
        reply_to_username=reply_to_username,
        reply_to_display_name=reply_to_display_name,
    )
    db.save_incoming_message(sender_id=sender_id, text=text, chat_id=chat_id)

    command_name = normalize_command(text)
    command = COMMANDS.get(command_name)
    if command is None:
        return "No conozco ese comando. Escribi help para ver las opciones."

    if context.user_level < command.min_level:
        return command.permission_error or DEFAULT_PERMISSION_ERROR

    return command.handler(context, db)


def _resolve_target_user(context: CommandContext, db: Database):
    if context.reply_to_user_id:
        return db.get_or_create_user(
            context.reply_to_user_id,
            context.reply_to_display_name,
            context.reply_to_username,
        )

    target = context.args.split(maxsplit=1)[0] if context.args else ""
    if not target:
        return None

    if target.startswith("@"):
        return db.get_user_by_username(target)

    if target.isdigit():
        return db.get_or_create_user(target)

    return db.get_user_by_username(target)


def _format_user(user) -> str:
    if user.username:
        return f"{user.user_id} (@{user.username})"
    if user.display_name:
        return f"{user.user_id} ({user.display_name})"
    return user.user_id


def _sum_chat_stats(rows) -> dict[str, int]:
    totals = {"total": 0, "active": 0, "inactive": 0}
    for row in rows:
        totals["total"] += row.total
        totals["active"] += row.active
        totals["inactive"] += row.inactive
    return totals
