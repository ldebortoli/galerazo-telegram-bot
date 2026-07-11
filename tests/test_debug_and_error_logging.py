import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import Update

from galerazo_bot.telegram_bot import _send_debug_update, _send_unhandled_error_event, _serialize_update


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def send_message(self, **kwargs) -> None:
        self.messages.append(kwargs)


class DebugSerializationTests(unittest.IsolatedAsyncioTestCase):
    def test_serializes_ptb_update_as_indented_json(self) -> None:
        serialized = _serialize_update(Update(update_id=17))
        self.assertEqual(json.loads(serialized)["update_id"], 17)
        self.assertIn("\n", serialized)

    async def test_debug_sends_plain_json_without_markdown_fences(self) -> None:
        message = SimpleNamespace(
            chat=SimpleNamespace(id=-1),
            message_id=10,
            reply_text=AsyncMock(),
            reply_document=AsyncMock(),
        )
        db = MagicMock()
        db.get_chat_settings.return_value = SimpleNamespace(language="es")

        sent = await _send_debug_update(db, message, Update(update_id=17))

        self.assertTrue(sent)
        payload = message.reply_text.await_args.kwargs["text"]
        self.assertEqual(json.loads(payload)["update_id"], 17)
        self.assertNotIn("```", payload)
        message.reply_document.assert_not_awaited()

    async def test_large_debug_uses_requested_filename_without_caption(self) -> None:
        message = SimpleNamespace(
            chat=SimpleNamespace(id=-1),
            message_id=10,
            reply_text=AsyncMock(),
            reply_document=AsyncMock(),
        )
        db = MagicMock()
        with tempfile.TemporaryDirectory() as directory:
            real_path = Path
            with (
                patch(
                    "galerazo_bot.telegram_bot._serialize_update",
                    return_value='{"data":"' + ("x" * 5000) + '"}',
                ),
                patch(
                    "galerazo_bot.telegram_bot.Path",
                    side_effect=lambda value: real_path(directory) / value,
                ),
            ):
                sent = await _send_debug_update(db, message, Update(update_id=91))

            document = message.reply_document.await_args.kwargs["document"]
            self.assertEqual(document.name, "Debug de la update 91")
            self.assertNotIn("caption", message.reply_document.await_args.kwargs)
            self.assertTrue(document.exists())

        self.assertTrue(sent)
        message.reply_text.assert_not_awaited()

    async def test_unhandled_error_log_includes_update_json(self) -> None:
        bot = FakeBot()
        await _send_unhandled_error_event(
            bot,
            "-100123",
            RuntimeError("failure"),
            Update(update_id=23),
        )

        self.assertEqual(len(bot.messages), 1)
        text = str(bot.messages[0]["text"])
        self.assertIn("Error no handleado", text)
        self.assertIn("Update JSON", text)
        self.assertIn('"update_id": 23', text)


if __name__ == "__main__":
    unittest.main()
