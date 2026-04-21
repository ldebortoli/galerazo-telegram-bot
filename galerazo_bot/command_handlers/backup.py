from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..roles import CommandContext, UserLevel


async def handle(context: CommandContext, _db: Database) -> str | None:
    if context.create_backup is None:
        return context.t("backup.not_configured")

    result = await context.create_backup()
    if result.sent:
        return None

    size_mb = result.size_bytes / 1024 / 1024
    limit_mb = result.max_size_bytes / 1024 / 1024
    return context.t("backup.too_large", size_mb=size_mb, limit_mb=limit_mb, path=result.path)


COMMANDS = {
    "backup": Command("backup", "envia un backup de la base de datos", handle, UserLevel.DEV),
}
