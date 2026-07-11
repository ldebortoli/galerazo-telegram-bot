from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from galerazo_bot.commands import handle_command_async
from galerazo_bot.database import Database, Trigger
from galerazo_bot.roles import TriggerPayload
from galerazo_bot.telegram_bot import _send_trigger_message, _trigger_payload_from_message


def _message(**changes):
    values = {
        "text": None,
        "photo": None,
        "video": None,
        "audio": None,
        "voice": None,
        "document": None,
        "video_note": None,
        "sticker": None,
        "dice": None,
        "caption": None,
    }
    values.update(changes)
    return SimpleNamespace(**values)


class TriggerTests(unittest.TestCase):
    def test_trigger_names_can_contain_spaces_and_delete_aliases_work(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            db.get_or_create_user("1", "User")
            db.register_chat("-1", "group", "Group")

            response = asyncio.run(
                handle_command_async(
                    "/agregartrigger cinco letras",
                    "1",
                    db,
                    chat_id="-1",
                    chat_type="group",
                    reply_to_trigger_payload=TriggerPayload(text="respuesta"),
                )
            )
            self.assertIn("cinco letras", response)
            self.assertIsNotNone(db.get_trigger("-1", "cinco letras"))

            response = asyncio.run(
                handle_command_async(
                    "/eltrigger cinco letras",
                    "1",
                    db,
                    chat_id="-1",
                    chat_type="group",
                )
            )
            self.assertIn("cinco letras", response)
            self.assertIsNone(db.get_trigger("-1", "cinco letras"))

    def test_stickers_and_dice_are_extracted_and_sent(self) -> None:
        sticker_payload = _trigger_payload_from_message(
            _message(sticker=SimpleNamespace(file_id="sticker-id"))
        )
        dice_payload = _trigger_payload_from_message(
            _message(dice=SimpleNamespace(emoji="🎲"))
        )

        self.assertEqual(sticker_payload, TriggerPayload(media_type="sticker", file_id="sticker-id"))
        self.assertEqual(dice_payload, TriggerPayload(text="🎲", media_type="dice"))

        bot = SimpleNamespace(send_sticker=AsyncMock(), send_dice=AsyncMock())
        asyncio.run(
            _send_trigger_message(
                bot,
                -1,
                Trigger("-1", "sticker", "Sticker", None, "sticker", "sticker-id", None, "1", "now"),
            )
        )
        asyncio.run(
            _send_trigger_message(
                bot,
                -1,
                Trigger("-1", "dados", "Dados", "🎲", "dice", None, None, "1", "now"),
            )
        )

        bot.send_sticker.assert_awaited_once_with(chat_id=-1, sticker="sticker-id")
        bot.send_dice.assert_awaited_once_with(chat_id=-1, emoji="🎲")


if __name__ == "__main__":
    unittest.main()
