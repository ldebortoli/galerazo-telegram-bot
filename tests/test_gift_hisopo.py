from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from galerazo_bot.command_handlers import regalar_hisopo
from galerazo_bot.commands import handle_command_async
from galerazo_bot.database import Database
from galerazo_bot.roles import UserLevel
from galerazo_bot.telegram_bot import _suggested_bot_commands


class GiftHisopoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.directory.name) / "test.sqlite3")
        self.db.get_or_create_user("1", "Developer")

    def tearDown(self) -> None:
        self.directory.cleanup()

    def run_command(self, text: str, level: UserLevel = UserLevel.DEV) -> str | None:
        return asyncio.run(
            handle_command_async(
                text,
                "1",
                self.db,
                chat_id="1",
                chat_type="private",
                user_level=level,
            )
        )

    def test_command_is_dev_only_and_hidden(self) -> None:
        denied = self.run_command(
            "/regalarhisopo invisible 267832653",
            UserLevel.COMMON,
        )
        self.assertEqual(denied, "No tenés permisos suficientes para usar este comando.")
        self.assertEqual(self.db.get_paid_hisopo_ownership("267832653"), [])

        dev_help = self.run_command("/help")
        self.assertNotIn("regalarhisopo", dev_help)
        for level in UserLevel:
            with self.subTest(level=level):
                names = {
                    command.command
                    for command in _suggested_bot_commands("es", level, True)
                }
                self.assertNotIn("regalarhisopo", names)

    def test_usage_unknown_type_and_invalid_user_ids(self) -> None:
        usage = self.run_command("/regalarhisopo")
        self.assertIn("/regalarhisopo tipo user_id", usage)
        self.assertIn("estelar", usage)
        self.assertIn("Uso", self.run_command("/regalarhisopo dengue 2 extra"))
        self.assertIn("no existe", self.run_command("/regalarhisopo inventado 2"))
        for invalid_id in ("１２", "abc", "0"):
            with self.subTest(user_id=invalid_id):
                self.assertIn(
                    "entero positivo",
                    self.run_command(f"/regalarhisopo dengue {invalid_id}"),
                )

    def test_command_only_operates_in_private_chat(self) -> None:
        response = asyncio.run(
            handle_command_async(
                "/regalarhisopo dengue 267832653",
                "1",
                self.db,
                chat_id="-1",
                chat_type="group",
                user_level=UserLevel.DEV,
            )
        )
        self.assertIn("chat privado", response)
        self.assertEqual(self.db.get_paid_hisopo_ownership("267832653"), [])

    def test_gifts_increment_global_ownership_and_leave_an_audit_trail(self) -> None:
        first = self.run_command("/regalarhisopo big-bang 267832653")
        second = self.run_command("/regalarhisopo hisopo_big_bang 267832653")
        bacteriophage = self.run_command("/regalarhisopo bacteriófago 267832653")
        stellar = self.run_command("/regalarhisopo estrella 267832653")

        self.assertIn("Hisopo Big Bang", first)
        self.assertIn("Ahora tiene 1", first)
        self.assertIn("Ahora tiene 2", second)
        self.assertIn("Hisopo Bacteriófago", bacteriophage)
        self.assertIn("Hisopo Estelar", stellar)
        ownership = {
            entry.hisopo_key: entry.quantity
            for entry in self.db.get_paid_hisopo_ownership("267832653")
        }
        self.assertEqual(
            ownership,
            {"big_bang": 2, "bacteriophage": 1, "stellar": 1},
        )
        self.assertIsNone(self.db.get_club_membership("267832653"))
        with self.db._connect() as conn:
            gifts = conn.execute(
                """
                SELECT gifted_by_user_id, recipient_user_id, hisopo_key
                FROM paid_hisopo_gifts ORDER BY gift_id
                """
            ).fetchall()
        self.assertEqual(
            [(row[0], row[1], row[2]) for row in gifts],
            [
                ("1", "267832653", "big_bang"),
                ("1", "267832653", "big_bang"),
                ("1", "267832653", "bacteriophage"),
                ("1", "267832653", "stellar"),
            ],
        )

    def test_database_accepts_a_deterministic_gift_timestamp(self) -> None:
        quantity = self.db.grant_paid_hisopo(
            recipient_user_id="2",
            hisopo_key="invisible",
            gifted_by_user_id="1",
            gifted_at="2026-08-28T12:00:00+00:00",
        )
        self.assertEqual(quantity, 1)
        ownership = self.db.get_paid_hisopo_ownership("2")[0]
        self.assertEqual(
            (ownership.hisopo_key, ownership.first_acquired_at, ownership.last_acquired_at),
            ("invisible", "2026-08-28T12:00:00+00:00", "2026-08-28T12:00:00+00:00"),
        )

    def test_all_documented_type_selectors_resolve(self) -> None:
        for selector in regalar_hisopo.GIFT_TYPE_HINTS:
            with self.subTest(selector=selector):
                normalized = regalar_hisopo._normalize_selector(selector)
                self.assertIn(normalized, regalar_hisopo.HISOPO_BY_GIFT_ALIAS)


if __name__ == "__main__":
    unittest.main()
