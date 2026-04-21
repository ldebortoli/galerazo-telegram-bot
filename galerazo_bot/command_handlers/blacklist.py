from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext, UserLevel


def bloquear(context: CommandContext, db: Database) -> str:
    target = _resolve_target_user(context, db)
    if target is None:
        return context.t("blacklist.block_usage")

    if target.user_id == context.sender_id:
        return context.t("blacklist.cannot_block_self")

    db.block_user(user_id=target.user_id, blocked_by_user_id=context.sender_id)
    return context.t("blacklist.blocked", user=_format_user(target))


def desbloquear(context: CommandContext, db: Database) -> str:
    target = _resolve_target_user(context, db)
    if target is None:
        return context.t("blacklist.unblock_usage")

    was_blocked = db.unblock_user(target.user_id)
    if not was_blocked:
        return context.t("blacklist.not_blocked", user=_format_user(target))

    return context.t("blacklist.unblocked", user=_format_user(target))


def listanegra(_context: CommandContext, db: Database) -> str:
    blocked_users = db.list_blocked_users()
    if not blocked_users:
        return _context.t("blacklist.empty")

    lines = [_context.t("blacklist.header")]
    for user in blocked_users:
        username = f"@{user.username}" if user.username else _context.t("blacklist.no_username")
        display_name = f" - {user.display_name}" if user.display_name else ""
        lines.append(f"- {user.user_id} ({username}){display_name}")
    return "\n".join(lines)


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


COMMANDS = {
    "bloquear": Command("bloquear", "bloquea un usuario", bloquear, UserLevel.DEV),
    "desbloquear": Command("desbloquear", "desbloquea un usuario", desbloquear, UserLevel.DEV),
    "desloquear": Command("desloquear", "desbloquea un usuario", desbloquear, UserLevel.DEV),
    "listanegra": Command("listanegra", "muestra usuarios bloqueados", listanegra, UserLevel.DEV, list_response=True),
}
