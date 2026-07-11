from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from telegram import Chat, Message, Update, User

from galerazo_bot.database import Database, GalerazaScore
from galerazo_bot.galeraza import build_galeraza_lines, render_galeraza_page
from galerazo_bot.telegram_bot import _galeraza_game_date, _is_galeraza_candidate


class GalerazaRenderingTests(unittest.TestCase):
    def test_uses_display_names_and_never_mentions_usernames(self) -> None:
        scores = [
            GalerazaScore("1", "alias", "Nombre Visible", 3),
            GalerazaScore("2", "alias_sin_nombre", None, 2),
            GalerazaScore("3", None, None, 1),
        ]

        lines = build_galeraza_lines(scores, language="es")

        self.assertEqual(
            lines,
            [
                "Nombre Visible (1) => 3",
                "alias_sin_nombre (2) => 2",
                "Usuario (3) => 1",
            ],
        )
        self.assertNotIn("@", "\n".join(lines))

    def test_uses_table_title(self) -> None:
        page = render_galeraza_page([], page=1, language="es")

        self.assertTrue(page.text.startswith("Tabla de Galerazas"))


class GalerazaAwardTests(unittest.TestCase):
    def _message(self, sent_at: datetime, user: User | None = None, **kwargs) -> Message:
        sender = user or User(id=1, first_name="User", is_bot=False)
        return Message(
            message_id=10,
            date=sent_at,
            chat=Chat(id=-1, type="group"),
            from_user=sender,
            **kwargs,
        )

    def test_telegram_timestamp_is_converted_to_argentina_date(self) -> None:
        before_midnight = self._message(
            datetime(2026, 7, 11, 2, 59, 59, tzinfo=timezone.utc),
            text="before",
        )
        at_midnight = self._message(
            datetime(2026, 7, 11, 3, 0, 0, tzinfo=timezone.utc),
            text="after",
        )

        self.assertEqual(_galeraza_game_date(before_midnight), "2026-07-10")
        self.assertEqual(_galeraza_game_date(at_midnight), "2026-07-11")

    def test_only_original_user_messages_are_candidates(self) -> None:
        sent_at = datetime(2026, 7, 11, 4, 0, tzinfo=timezone.utc)
        user = User(id=1, first_name="User", is_bot=False)
        message = self._message(sent_at, user, text="original")

        self.assertTrue(_is_galeraza_candidate(Update(1, message=message), message, user))
        self.assertFalse(
            _is_galeraza_candidate(Update(2, edited_message=message), message, user)
        )

        bot = User(id=2, first_name="Bot", is_bot=True)
        bot_message = self._message(sent_at, bot, text="bot")
        self.assertFalse(
            _is_galeraza_candidate(Update(3, message=bot_message), bot_message, bot)
        )

        service_message = self._message(sent_at, user, new_chat_members=(user,))
        self.assertFalse(
            _is_galeraza_candidate(
                Update(4, message=service_message),
                service_message,
                user,
            )
        )

    def test_winner_persists_telegram_message_date(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            db.register_chat("-1", "group", "Group")
            message_date = "2026-07-11T03:00:00+00:00"

            self.assertTrue(
                db.try_award_daily_galeraza(
                    "-1",
                    "2026-07-11",
                    "1",
                    "10",
                    message_date,
                )
            )
            with db._connect() as conn:
                row = conn.execute(
                    "SELECT message_date FROM galeraza_daily_winners"
                ).fetchone()

            self.assertEqual(row["message_date"], message_date)


if __name__ == "__main__":
    unittest.main()
