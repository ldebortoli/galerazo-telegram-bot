from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext, UserLevel
from ..user_display import format_user, resolve_target_user


GALERAZO_BOT_USER_ID = "573379301"


def bloquear(context: CommandContext, db: Database) -> str:
    target = resolve_target_user(context, db)
    if target is None:
        return context.t("blacklist.block_usage")

    if target.user_id == context.sender_id:
        return context.t("blacklist.cannot_block_self")
    if target.user_id in {context.bot_user_id, GALERAZO_BOT_USER_ID}:
        return context.t("blacklist.cannot_block_bot")

    db.block_user(user_id=target.user_id, blocked_by_user_id=context.sender_id)
    return context.t("blacklist.blocked", user=format_user(target, context))


def desbloquear(context: CommandContext, db: Database) -> str:
    target = resolve_target_user(context, db)
    if target is None:
        return context.t("blacklist.unblock_usage")

    was_blocked = db.unblock_user(target.user_id)
    if not was_blocked:
        return context.t("blacklist.not_blocked", user=format_user(target, context))

    return context.t("blacklist.unblocked", user=format_user(target, context))


def listanegra(_context: CommandContext, db: Database) -> str:
    blocked_users = db.list_blocked_users()
    if not blocked_users:
        return _context.t("blacklist.empty")

    lines = [_context.t("blacklist.header")]
    for user in blocked_users:
        lines.append(f"- {format_user(user, _context)}")
    return "\n".join(lines)


COMMANDS = {
    "bloquear": Command("bloquear", "bloquea un usuario", bloquear, UserLevel.DEV),
    "desbloquear": Command("desbloquear", "desbloquea un usuario", desbloquear, UserLevel.DEV),
    "desloquear": Command("desloquear", "desbloquea un usuario", desbloquear, UserLevel.DEV),
    "listanegra": Command("listanegra", "muestra usuarios bloqueados", listanegra, UserLevel.DEV, list_response=True),
    "bloqueados": Command("bloqueados", "muestra usuarios bloqueados", listanegra, UserLevel.DEV, list_response=True),
}
