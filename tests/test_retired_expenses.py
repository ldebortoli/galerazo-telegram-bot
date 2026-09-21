from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from galerazo_bot.commands import get_command, handle_command_async
from galerazo_bot.database import Database
from galerazo_bot.roles import UserLevel


RETIRED_COMMANDS = (
    "gasto", "pagoresumen", "cierre", "ayudagastos", "ultimosgastos",
    "estadogastos", "sincronizargastos", "habilitargastos", "deshabilitargastos",
)


class RetiredExpenseTests(unittest.IsolatedAsyncioTestCase):
    async def test_retired_commands_are_unavailable_for_every_role_and_chat(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            db.get_or_create_user("1", "User")
            for level in UserLevel:
                for chat_type in ("private", "group", "supergroup"):
                    help_text = await handle_command_async(
                        "/help", "1", db, chat_id="1", chat_type=chat_type,
                        user_level=level,
                    )
                    for command in RETIRED_COMMANDS:
                        self.assertNotIn(f"/{command}", help_text)
                        for prefix in ("/", "!", ".", ">", "$"):
                            with self.subTest(level=level, chat=chat_type, command=command, prefix=prefix):
                                text = f"{prefix}{command}@galerazobot 100 | comida | efectivo | prueba"
                                self.assertIsNone(get_command(text))
                                self.assertIsNone(await handle_command_async(
                                    text, "1", db, chat_id="1", chat_type=chat_type,
                                    user_level=level,
                                ))
            with closing(sqlite3.connect(db.path)) as connection, connection:
                self.assertIsNone(connection.execute(
                    "SELECT name FROM sqlite_master WHERE name = 'expenses'"
                ).fetchone())

    def test_opening_existing_database_preserves_retired_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.sqlite3"
            # A legacy table is archival data: startup must neither migrate nor delete it.
            with closing(sqlite3.connect(path)) as connection, connection:
                connection.execute("""
                    CREATE TABLE expenses (
                        expense_id INTEGER PRIMARY KEY, chat_id TEXT, amount_cents INTEGER,
                        description TEXT, sheet_status TEXT, occurred_on TEXT
                    )
                """)
                connection.execute(
                    "INSERT INTO expenses VALUES (1, '-1', 12345, 'historial', 'pending', '')"
                )
                schema = connection.execute(
                    "SELECT sql FROM sqlite_master WHERE name = 'expenses'"
                ).fetchone()
                rows = connection.execute("SELECT * FROM expenses").fetchall()
            db = Database(path)
            db.get_or_create_user("1", "User")
            db.register_chat("-1", "group", "Group")
            self.assertTrue(db.migrate_chat_id("-1", "-1001"))
            reopened = Database(path)
            self.assertEqual(reopened.get_user("1").display_name, "User")
            with closing(sqlite3.connect(path)) as connection, connection:
                self.assertEqual(connection.execute(
                    "SELECT sql FROM sqlite_master WHERE name = 'expenses'"
                ).fetchone(), schema)
                self.assertEqual(connection.execute("SELECT * FROM expenses").fetchall(), rows)
