from __future__ import annotations

from typing import Protocol

from .database import Database
from .roles import CommandContext


class DisplayableUser(Protocol):
    user_id: str
    display_name: str | None
    username: str | None


def resolve_target_user(context: CommandContext, db: Database):
    if context.reply_to_user_id:
        return db.get_or_create_user(
            context.reply_to_user_id,
            context.reply_to_display_name,
            context.reply_to_username,
        )

    target = context.args.split(maxsplit=1)[0] if context.args else ""
    if not target:
        return None
    if target.isdigit():
        return db.get_or_create_user(target)
    return db.get_user_by_username(target)


def format_user(user: DisplayableUser, context: CommandContext) -> str:
    name = user.display_name or user.username or context.t("user.unknown")
    return f"{name} ({user.user_id})"
