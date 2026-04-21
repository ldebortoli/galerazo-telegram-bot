from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext


def handle(context: CommandContext, db: Database) -> str:
    stats_by_type = {row.chat_type: row for row in db.get_chat_stats()}
    types = {
        "private": context.t("chats.private"),
        "group": context.t("chats.group"),
        "supergroup": context.t("chats.supergroup"),
        "channel": context.t("chats.channel"),
    }
    totals = _sum_chat_stats(stats_by_type.values())

    lines = [
        context.t("chats.header"),
        context.t("chats.total", total=totals["total"]),
        context.t("chats.active", active=totals["active"]),
        context.t("chats.inactive", inactive=totals["inactive"]),
        "",
        context.t("chats.by_type"),
    ]

    for chat_type, label in types.items():
        row = stats_by_type.get(chat_type)
        total = row.total if row else 0
        active = row.active if row else 0
        inactive = row.inactive if row else 0
        lines.append(context.t("chats.type_row", label=label, total=total, active=active, inactive=inactive))

    return "\n".join(lines)


def _sum_chat_stats(rows) -> dict[str, int]:
    totals = {"total": 0, "active": 0, "inactive": 0}
    for row in rows:
        totals["total"] += row.total
        totals["active"] += row.active
        totals["inactive"] += row.inactive
    return totals


COMMANDS = {
    "chats": Command("chats", "muestra estadisticas de chats", handle),
}
