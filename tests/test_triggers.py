from __future__ import annotations

import asyncio
import json
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
        "animation": None,
        "audio": None,
        "voice": None,
        "document": None,
        "video_note": None,
        "sticker": None,
        "dice": None,
        "contact": None,
        "location": None,
        "venue": None,
        "poll": None,
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

    def test_structured_and_animation_payloads_are_recreated(self) -> None:
        contact = SimpleNamespace(
            phone_number="123",
            first_name="Ada",
            last_name="Lovelace",
            vcard=None,
        )
        contact_payload = _trigger_payload_from_message(_message(contact=contact))
        animation_payload = _trigger_payload_from_message(
            _message(animation=SimpleNamespace(file_id="animation-id"), caption="caption")
        )

        self.assertEqual(contact_payload.media_type, "contact")
        self.assertEqual(
            contact_payload.data,
            {"phone_number": "123", "first_name": "Ada", "last_name": "Lovelace"},
        )
        self.assertEqual(
            animation_payload,
            TriggerPayload(
                media_type="animation",
                file_id="animation-id",
                caption="caption",
            ),
        )

        bot = SimpleNamespace(send_contact=AsyncMock(), send_animation=AsyncMock())
        asyncio.run(
            _send_trigger_message(
                bot,
                -1,
                Trigger(
                    "-1",
                    "contacto",
                    "Contacto",
                    None,
                    "contact",
                    None,
                    None,
                    "1",
                    "now",
                    json.dumps(contact_payload.data),
                ),
            )
        )
        asyncio.run(
            _send_trigger_message(
                bot,
                -1,
                Trigger(
                    "-1",
                    "animacion",
                    "Animación",
                    None,
                    "animation",
                    "animation-id",
                    "caption",
                    "1",
                    "now",
                ),
            )
        )

        bot.send_contact.assert_awaited_once_with(
            chat_id=-1,
            phone_number="123",
            first_name="Ada",
            last_name="Lovelace",
        )
        bot.send_animation.assert_awaited_once_with(
            chat_id=-1,
            animation="animation-id",
            caption="caption",
        )

    def test_service_message_is_not_a_valid_trigger_payload(self) -> None:
        self.assertIsNone(_trigger_payload_from_message(_message()))

    def test_location_venue_and_poll_payloads_are_sent(self) -> None:
        bot = SimpleNamespace(
            send_location=AsyncMock(),
            send_venue=AsyncMock(),
            send_poll=AsyncMock(),
        )
        cases = (
            (
                "location",
                {"latitude": -34.6, "longitude": -58.4},
                bot.send_location,
            ),
            (
                "venue",
                {
                    "latitude": -34.6,
                    "longitude": -58.4,
                    "title": "Lugar",
                    "address": "Dirección",
                },
                bot.send_venue,
            ),
            (
                "poll",
                {
                    "question": "¿Sí o no?",
                    "options": ["Sí", "No"],
                    "is_anonymous": True,
                    "type": "regular",
                    "allows_multiple_answers": False,
                },
                bot.send_poll,
            ),
        )

        for media_type, payload, method in cases:
            with self.subTest(media_type=media_type):
                asyncio.run(
                    _send_trigger_message(
                        bot,
                        -1,
                        Trigger(
                            "-1",
                            media_type,
                            media_type,
                            None,
                            media_type,
                            None,
                            None,
                            "1",
                            "now",
                            json.dumps(payload, ensure_ascii=False),
                        ),
                    )
                )
                method.assert_awaited_once_with(chat_id=-1, **payload)


if __name__ == "__main__":
    unittest.main()
