from __future__ import annotations

import asyncio
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from telegram import Chat, Message, MessageEntity, Update, User
from telegram.ext import CommandHandler, MessageHandler, PrefixHandler

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

    def test_registered_commands_use_native_command_and_prefix_handlers(self) -> None:
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
        prefix_handlers = [
            handler
            for group, handler in application.handlers
            if group == 1 and isinstance(handler, PrefixHandler)
        ]
        self.assertEqual(len(prefix_handlers), 1)
        self.assertTrue(
            frozenset({f"{prefix}galerazas" for prefix in ("!", ".", ">", "$")})
            | frozenset({f"{prefix}galeraza" for prefix in ("!", ".", ">", "$")})
            <= prefix_handlers[0].commands,
        )
        self.assertFalse(
            any(group == 1 and isinstance(handler, MessageHandler) for group, handler in application.handlers)
        )

        message = Message(
            message_id=1,
            date=datetime(2026, 8, 8, tzinfo=timezone.utc),
            chat=Chat(id=-1, type="group"),
            from_user=User(id=1, first_name="User", is_bot=False),
            text="galerazas",
        )
        bare_update = Update(1, message=message)
        command_handlers = [
            handler
            for group, handler in application.handlers
            if group == 1 and isinstance(handler, CommandHandler)
        ]
        self.assertFalse(any(handler.check_update(bare_update) for handler in command_handlers))
        self.assertIsNone(prefix_handlers[0].check_update(bare_update))

        slash_message = Message(
            message_id=2,
            date=datetime(2026, 8, 8, tzinfo=timezone.utc),
            chat=message.chat,
            from_user=message.from_user,
            text="/galerazas",
            entities=(MessageEntity(type="bot_command", offset=0, length=10),),
        )
        slash_message.set_bot(type("Bot", (), {"username": "bot"})())
        slash_update = Update(2, message=slash_message)
        self.assertEqual(sum(bool(handler.check_update(slash_update)) for handler in command_handlers), 1)
        object.__setattr__(message, "text", "!galerazas")
        self.assertTrue(prefix_handlers[0].check_update(bare_update))

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

            for text in ("/inventado", "!inventado", "inventado", "galerazobot hola"):
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
                "/hola",
                "!hola",
                ".hola",
                ">hola",
                "$hola",
            ):
                with self.subTest(text=text):
                    response = asyncio.run(handle_command_async(text, "1", db))
                    self.assertIn("Test User", response)

    def test_commands_without_a_prefix_do_not_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            db.get_or_create_user("1", "Test User")

            response = asyncio.run(handle_command_async("hola", "1", db))

            self.assertIsNone(response)

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
            self.assertIn("/version:", response)
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
