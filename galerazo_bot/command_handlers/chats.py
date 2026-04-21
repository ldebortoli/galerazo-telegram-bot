from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext


def handle(_context: CommandContext, db: Database) -> str:
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
