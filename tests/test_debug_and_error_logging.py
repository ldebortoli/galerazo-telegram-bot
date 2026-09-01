import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import Chat, Message, Update
from telegram.error import BadRequest, TimedOut

from galerazo_bot.telegram_bot import (
    _is_stale_callback_query_error,
    _send_debug_update,
    _send_log_document,
    _send_unhandled_error_event,
    _serialize_update,
)


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []
        self.documents: list[dict[str, object]] = []

    async def send_message(self, **kwargs) -> None:
        self.messages.append(kwargs)

    async def send_document(self, **kwargs) -> None:
        self.documents.append(kwargs)


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

    async def test_large_debug_relies_on_global_timeout_policy(self) -> None:
        message = SimpleNamespace(
            reply_text=AsyncMock(),
            reply_document=AsyncMock(),
        )
        with patch("galerazo_bot.telegram_bot._serialize_update", return_value="x" * 5000):
            sent = await _send_debug_update(MagicMock(), message, Update(update_id=92))

        self.assertTrue(sent)
        self.assertEqual(message.reply_document.await_count, 1)

    async def test_large_debug_returns_false_after_global_policy_fails(self) -> None:
        message = SimpleNamespace(
            reply_text=AsyncMock(),
            reply_document=AsyncMock(side_effect=TimedOut()),
        )
        with patch("galerazo_bot.telegram_bot._serialize_update", return_value="x" * 5000):
            sent = await _send_debug_update(MagicMock(), message, Update(update_id=93))

        self.assertFalse(sent)
        self.assertEqual(message.reply_document.await_count, 1)

    async def test_small_debug_returns_false_on_telegram_error(self) -> None:
        message = SimpleNamespace(
            reply_text=AsyncMock(side_effect=BadRequest("rejected")),
            reply_document=AsyncMock(),
        )

        sent = await _send_debug_update(MagicMock(), message, Update(update_id=94))

        self.assertFalse(sent)
        message.reply_document.assert_not_awaited()

    async def test_unhandled_error_sends_summary_and_full_debug_txt(self) -> None:
        bot = FakeBot()
        await _send_unhandled_error_event(
            bot,
            "-100123",
            RuntimeError("failure"),
            Update(update_id=23),
        )

        self.assertEqual(len(bot.messages), 1)
        self.assertEqual(bot.messages[0]["text"], "RuntimeError: failure")
        self.assertEqual(len(bot.documents), 1)
        arguments = bot.documents[0]
        debug_text = arguments["document"].getvalue().decode("utf-8")
        self.assertEqual(arguments["filename"], "Debug del error de la update 23.txt")
        self.assertIn("Error no handleado", debug_text)
        self.assertIn("RuntimeError: failure", debug_text)
        self.assertIn("Update JSON", debug_text)
        self.assertIn('"update_id": 23', debug_text)
        self.assertEqual(arguments["read_timeout"], 30)
        self.assertEqual(arguments["write_timeout"], 30)
        self.assertEqual(arguments["connect_timeout"], 30)
        self.assertEqual(arguments["pool_timeout"], 30)

    async def test_unhandled_error_without_log_chat_does_not_send_document(self) -> None:
        bot = FakeBot()

        await _send_unhandled_error_event(bot, None, RuntimeError("failure"), None)

        self.assertEqual(bot.messages, [])
        self.assertEqual(bot.documents, [])

    async def test_unhandled_error_summary_includes_update_chat_name_and_id(self) -> None:
        bot = FakeBot()
        chat = Chat(id=-100123, type="supergroup", title="Grupo de prueba")
        message = Message(
            message_id=10,
            date=datetime(2026, 9, 1, tzinfo=timezone.utc),
            chat=chat,
        )

        await _send_unhandled_error_event(
            bot,
            "-100999",
            RuntimeError("failure"),
            Update(update_id=24, message=message),
        )

        self.assertEqual(
            bot.messages[0]["text"],
            "RuntimeError: failure\nChat: Grupo de prueba (-100123)",
        )

    async def test_error_debug_document_relies_on_global_timeout_policy(self) -> None:
        bot = SimpleNamespace(send_document=AsyncMock())

        sent = await _send_log_document(bot, "-100123", b"debug", "debug.txt")

        self.assertTrue(sent)
        self.assertEqual(bot.send_document.await_count, 1)
        self.assertEqual(bot.send_document.await_args.kwargs["document"].getvalue(), b"debug")

    async def test_error_debug_document_returns_false_on_telegram_error(self) -> None:
        bot = SimpleNamespace(send_document=AsyncMock(side_effect=BadRequest("rejected")))

        sent = await _send_log_document(bot, "-100123", b"debug", "debug.txt")

        self.assertFalse(sent)
        self.assertEqual(bot.send_document.await_count, 1)

    def test_detects_only_stale_callback_query_bad_request(self) -> None:
        self.assertTrue(
            _is_stale_callback_query_error(
                BadRequest("Query is too old and response timeout expired or query ID is invalid")
            )
        )
        self.assertFalse(_is_stale_callback_query_error(BadRequest("message is too old")))
        self.assertFalse(_is_stale_callback_query_error(RuntimeError("query is too old")))


if __name__ == "__main__":
    unittest.main()
