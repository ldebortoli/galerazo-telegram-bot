from __future__ import annotations

import os
from pathlib import Path

from .config import load_settings
from .database import Database


def create_deploy_backup() -> Path:
    settings = load_settings()
    backups_path = Path(os.getenv("BACKUPS_PATH", "backups"))
    return Database(settings.database_path).create_backup(backups_path)


def main() -> int:
    backup_path = create_deploy_backup()
    print(f"Backup created: {backup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
