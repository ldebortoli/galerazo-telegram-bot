import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import Update
from telegram.error import BadRequest, TimedOut

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
        debug_json = '{"data":"' + ("x" * 5000) + '"}'
        with patch("galerazo_bot.telegram_bot._serialize_update", return_value=debug_json):
            sent = await _send_debug_update(db, message, Update(update_id=91))

        arguments = message.reply_document.await_args.kwargs
        self.assertEqual(arguments["document"].getvalue(), debug_json.encode("utf-8"))
        self.assertEqual(arguments["filename"], "Debug de la update 91")
        self.assertNotIn("caption", arguments)
        self.assertEqual(arguments["read_timeout"], 30)
        self.assertEqual(arguments["write_timeout"], 30)
        self.assertEqual(arguments["connect_timeout"], 30)
        self.assertEqual(arguments["pool_timeout"], 30)

        self.assertTrue(sent)
        message.reply_text.assert_not_awaited()

    async def test_large_debug_retries_one_timeout(self) -> None:
        message = SimpleNamespace(
            reply_text=AsyncMock(),
            reply_document=AsyncMock(side_effect=[TimedOut(), None]),
        )
        with patch("galerazo_bot.telegram_bot._serialize_update", return_value="x" * 5000):
            sent = await _send_debug_update(MagicMock(), message, Update(update_id=92))

        self.assertTrue(sent)
        self.assertEqual(message.reply_document.await_count, 2)

    async def test_large_debug_returns_false_after_second_timeout(self) -> None:
        message = SimpleNamespace(
            reply_text=AsyncMock(),
            reply_document=AsyncMock(side_effect=TimedOut()),
        )
        with patch("galerazo_bot.telegram_bot._serialize_update", return_value="x" * 5000):
            sent = await _send_debug_update(MagicMock(), message, Update(update_id=93))

        self.assertFalse(sent)
        self.assertEqual(message.reply_document.await_count, 2)

    async def test_small_debug_returns_false_on_telegram_error(self) -> None:
        message = SimpleNamespace(
            reply_text=AsyncMock(side_effect=BadRequest("rejected")),
            reply_document=AsyncMock(),
        )

        sent = await _send_debug_update(MagicMock(), message, Update(update_id=94))

        self.assertFalse(sent)
        message.reply_document.assert_not_awaited()

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
        self.assertTrue(text.startswith("RuntimeError: failure\n"))
        self.assertIn("Error no handleado", text)
        self.assertIn("Update JSON", text)
        self.assertIn('"update_id": 23', text)


if __name__ == "__main__":
    unittest.main()
