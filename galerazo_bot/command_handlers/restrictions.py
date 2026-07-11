from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext, UserLevel
from ..user_display import format_user, resolve_target_user


def restringir(context: CommandContext, db: Database) -> str:
    if context.chat_type not in {"group", "supergroup"} or context.chat_id is None:
        return context.t("restrictions.group_only")

    target = resolve_target_user(context, db)
    if target is None:
        return context.t("restrictions.restrict_usage")
    if target.user_id == context.sender_id:
        return context.t("restrictions.cannot_restrict_self")

    db.restrict_user_in_chat(
        chat_id=context.chat_id,
        user_id=target.user_id,
        restricted_by_user_id=context.sender_id,
    )
    return context.t("restrictions.restricted", user=format_user(target, context))


def habilitar(context: CommandContext, db: Database) -> str:
    if context.chat_type not in {"group", "supergroup"} or context.chat_id is None:
        return context.t("restrictions.group_only")

    target = resolve_target_user(context, db)
    if target is None:
        return context.t("restrictions.enable_usage")

    was_enabled = db.unrestrict_user_in_chat(context.chat_id, target.user_id)
    if not was_enabled:
        return context.t("restrictions.not_restricted", user=format_user(target, context))

    return context.t("restrictions.enabled", user=format_user(target, context))


def restringidos(context: CommandContext, db: Database) -> str:
    if context.chat_type not in {"group", "supergroup"} or context.chat_id is None:
        return context.t("restrictions.group_only")

    users = db.list_restricted_users_in_chat(context.chat_id)
    if not users:
        return context.t("restrictions.empty")

    lines = [context.t("restrictions.header")]
    for user in users:
        lines.append(f"- {format_user(user, context)}")
    return "\n".join(lines)


COMMANDS = {
    "restringir": Command(
        "restringir",
        "restringe un usuario en este chat",
        restringir,
        UserLevel.ADMIN,
    ),
    "habilitar": Command(
        "habilitar",
        "habilita un usuario restringido en este chat",
        habilitar,
        UserLevel.ADMIN,
    ),
    "restringidos": Command(
        "restringidos",
        "muestra usuarios restringidos en este chat",
        restringidos,
        UserLevel.ADMIN,
        list_response=True,
    ),
}
