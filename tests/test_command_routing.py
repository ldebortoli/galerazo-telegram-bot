from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from telegram.ext import CommandHandler

from galerazo_bot.commands import handle_command_async
from galerazo_bot.database import Database
from galerazo_bot.telegram_bot import _register_handlers


class CapturingApplication:
    def __init__(self) -> None:
        self.handlers: list[tuple[int, object]] = []

    def add_handler(self, handler, group: int = 0) -> None:
        self.handlers.append((group, handler))


class CommandRoutingTests(unittest.TestCase):
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

            response = asyncio.run(
                handle_command_async(
                    text="/galerazas",
                    sender_id="1",
                    db=db,
                    chat_id="-1",
                    chat_type="group",
                    send_galerazas=send_galerazas,
                )
            )

            self.assertIsNone(response)
            self.assertEqual(calls, 1)


if __name__ == "__main__":
    unittest.main()
