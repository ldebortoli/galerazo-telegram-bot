from __future__ import annotations

import asyncio
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from telegram import Chat, Message, Update, User
from telegram.ext import CommandHandler, MessageHandler

from galerazo_bot.commands import handle_command_async
from galerazo_bot.database import Database
from galerazo_bot.telegram_bot import POLLING_OPTIONS, _build_application, _register_handlers
from galerazo_bot.update_processor import PerChatUpdateProcessor


class CapturingApplication:
    def __init__(self) -> None:
        self.handlers: list[tuple[int, object]] = []

    def add_handler(self, handler, group: int = 0) -> None:
        self.handlers.append((group, handler))


class CommandRoutingTests(unittest.TestCase):
    def test_polling_keeps_pending_updates(self) -> None:
        self.assertFalse(POLLING_OPTIONS["drop_pending_updates"])

    def test_application_uses_per_chat_update_processor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            application = _build_application("123456:TEST_TOKEN", db)

        self.assertIsInstance(application.update_processor, PerChatUpdateProcessor)
        self.assertEqual(application.concurrent_updates, 256)
        self.assertIsNotNone(application.job_queue)

    def test_registered_commands_have_no_unknown_command_fallback(self) -> None:
        application = CapturingApplication()

        _register_handlers(application)

        self.assertFalse(any(group == 2 for group, _handler in application.handlers))
        galerazas_handlers = [
            handler
            for group, handler in application.handlers
            if group == 1
            and isinstance(handler, CommandHandler)
            and "galerazas" in handler.commands
        ]
        self.assertEqual(len(galerazas_handlers), 1)
        galeraza_alias_handlers = [
            handler
            for group, handler in application.handlers
            if group == 1
            and isinstance(handler, CommandHandler)
            and "galeraza" in handler.commands
        ]
        self.assertEqual(len(galeraza_alias_handlers), 1)

    def test_preprocessor_receives_pin_add_and_leave_events(self) -> None:
        application = CapturingApplication()
        _register_handlers(application)
        preprocessors = [
            handler
            for group, handler in application.handlers
            if group == 0 and isinstance(handler, MessageHandler)
        ]
        self.assertEqual(len(preprocessors), 1)

        sent_at = datetime(2026, 7, 15, tzinfo=timezone.utc)
        actor = User(id=1, first_name="Actor", is_bot=False)
        other_user = User(id=2, first_name="Other", is_bot=False)
        pinned_message = Message(
            message_id=9,
            date=sent_at,
            chat=Chat(id=-1, type="group"),
            from_user=other_user,
            text="pinned",
        )
        cases = (
            {"pinned_message": pinned_message},
            {"new_chat_members": (other_user,)},
            {"left_chat_member": other_user},
        )
        for update_id, kwargs in enumerate(cases, start=10):
            with self.subTest(field=next(iter(kwargs))):
                message = Message(
                    message_id=update_id,
                    date=sent_at,
                    chat=Chat(id=-1, type="group"),
                    from_user=actor,
                    **kwargs,
                )
                self.assertTrue(
                    preprocessors[0].check_update(Update(update_id, message=message))
                )

    def test_unknown_commands_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            db.get_or_create_user("1", "Test User")

            for text in ("/inventado", "!inventado", "inventado"):
                response = asyncio.run(
                    handle_command_async(
                        text=text,
                        sender_id="1",
                        db=db,
                    )
                )
                self.assertIsNone(response)

    def test_supported_command_prefixes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            db.get_or_create_user("1", "Test User")

            for text in (
                ".hola",
                ">hola",
                "$hola",
                "galerazobot hola",
                "Galerazo_Bot hola",
            ):
                with self.subTest(text=text):
                    response = asyncio.run(handle_command_async(text, "1", db))
                    self.assertIn("Test User", response)

    def test_galerazas_handler_returns_no_second_response(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            db.get_or_create_user("1", "Test User")
            db.register_chat("-1", "group", "Test Group")
            calls = 0

            async def send_galerazas() -> bool:
                nonlocal calls
                calls += 1
                return True

            for command_text in ("/galerazas", "/galeraza"):
                with self.subTest(command_text=command_text):
                    response = asyncio.run(
                        handle_command_async(
                            text=command_text,
                            sender_id="1",
                            db=db,
                            chat_id="-1",
                            chat_type="group",
                            send_galerazas=send_galerazas,
                        )
                    )

                    self.assertIsNone(response)
            self.assertEqual(calls, 2)

    def test_help_uses_slash_prefixed_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            db.get_or_create_user("1", "Test User")

            response = asyncio.run(handle_command_async("/help", "1", db))

            self.assertIn("/help:", response)
            self.assertIn("/start:", response)
            self.assertNotIn("- help:", response)

    def test_start_greets_and_points_to_help(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            db.get_or_create_user("1", "Test User")

            response = asyncio.run(handle_command_async("/start", "1", db))

            self.assertIn("Test User", response)
            self.assertIn("/help", response)

    def test_lil_returns_lil(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            db.get_or_create_user("1", "Test User")

            response = asyncio.run(handle_command_async("/lil", "1", db))

            self.assertEqual(response, "LIL")


if __name__ == "__main__":
    unittest.main()
