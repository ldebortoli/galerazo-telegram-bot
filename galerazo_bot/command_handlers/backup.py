from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext, UserLevel


async def handle(context: CommandContext, _db: Database) -> str | None:
    if context.create_backup is None:
        return "No hay mecanismo de backup configurado."

    result = await context.create_backup()
    if result.sent:
        return None

    size_mb = result.size_bytes / 1024 / 1024
    limit_mb = result.max_size_bytes / 1024 / 1024
    return (
        "El backup no entra en el limite de Telegram "
        f"({size_mb:.2f} MB de {limit_mb:.0f} MB). "
        f"Deje un backup local en: {result.path}"
    )


COMMANDS = {
    "backup": Command("backup", "envia un backup de la base de datos", handle, UserLevel.DEV),
}
