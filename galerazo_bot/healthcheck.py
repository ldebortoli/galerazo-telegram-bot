from __future__ import annotations

import sqlite3
from contextlib import closing

from .config import load_settings


def check_database() -> None:
    database_path = load_settings().database_path.resolve()
    if not database_path.is_file():
        raise RuntimeError(f"Database does not exist: {database_path}")

    database_uri = f"{database_path.as_uri()}?mode=ro"
    with closing(sqlite3.connect(database_uri, uri=True, timeout=2)) as connection:
        connection.execute("PRAGMA query_only=ON")
        result = connection.execute("SELECT 1").fetchone()
    if result != (1,):
        raise RuntimeError("SQLite read check returned an unexpected result")


def main() -> int:
    try:
        check_database()
    except Exception as error:
        print(f"UNHEALTHY: {error}")
        return 1
    print("HEALTHY: SQLite is readable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
