from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import User
from telegram.error import TimedOut

from galerazo_bot.config import Settings
from galerazo_bot.database import HisopoCollectionEntry
from galerazo_bot.mini_app import MiniAppService
from galerazo_bot import telegram_bot as tb


def settings(**overrides) -> Settings:
    values = {
        "telegram_bot_token": "token",
        "telegram_dev_user_ids": frozenset(),
        "telegram_log_chat_id": None,
        "telegram_announcements_chat_id": None,
        "database_path": Path("db.sqlite3"),
        "google_sheets_credentials_json_path": None,
        "google_sheets_spreadsheet_id": None,
        "google_sheets_worksheet_name": "Gastos",
    }
    values.update(overrides)
    return Settings(**values)


def state(current_settings: Settings | None = None) -> tb.BotState:
    return tb.BotState(
        db=MagicMock(),
        settings=current_settings or settings(),
        bot_user_id="99",
        bot_username="galerazo_bot",
        expense_sheet_writer=MagicMock(),
        media_moderator=MagicMock(),
    )


class TelegramBotMonetizationTests(unittest.IsolatedAsyncioTestCase):
    async def test_payment_entrypoints_ignore_missing_and_delegate(self) -> None:
        bot_state = state()
        context = SimpleNamespace(
            application=SimpleNamespace(bot_data={"state": bot_state})
        )
        with patch.object(tb, "answer_pre_checkout_query", AsyncMock()) as precheckout:
            await tb._pre_checkout_query_entrypoint(SimpleNamespace(pre_checkout_query=None), context)
            precheckout.assert_not_awaited()
            query = object()
            await tb._pre_checkout_query_entrypoint(SimpleNamespace(pre_checkout_query=query), context)
            precheckout.assert_awaited_once_with(
                query=query,
                db=bot_state.db,
                bot_token="token",
            )

        empty_update = SimpleNamespace(effective_message=None)
        with patch.object(tb, "process_successful_payment", AsyncMock()) as success:
            await tb._successful_payment_entrypoint(empty_update, context)
            success.assert_not_awaited()
            message = object()
            await tb._successful_payment_entrypoint(SimpleNamespace(effective_message=message), context)
            success.assert_awaited_once_with(message=message, db=bot_state.db, bot_token="token")

        with patch.object(tb, "process_refunded_payment", AsyncMock()) as refund:
            await tb._refunded_payment_entrypoint(empty_update, context)
            refund.assert_not_awaited()
            message = object()
            await tb._refunded_payment_entrypoint(SimpleNamespace(effective_message=message), context)
            refund.assert_awaited_once_with(message=message, db=bot_state.db)

    async def test_post_shutdown_stops_only_real_service(self) -> None:
        app = SimpleNamespace(bot_data={})
        await tb._post_shutdown(app)

        runner = SimpleNamespace(cleanup=AsyncMock())
        service = MiniAppService(runner=runner, site=MagicMock())
        app.bot_data["mini_app_service"] = service
        await tb._post_shutdown(app)
        runner.cleanup.assert_awaited_once()

    async def test_configure_mini_app_disabled_invalid_success_and_button_failure(self) -> None:
        bot = SimpleNamespace(set_chat_menu_button=AsyncMock())
        app = SimpleNamespace(bot_data={"state": state(settings())}, bot=bot)
        self.assertFalse(await tb._configure_mini_app(app))

        app.bot_data["state"] = state(settings(telegram_mini_app_url="http://localhost"))
        self.assertFalse(await tb._configure_mini_app(app))

        configured_state = state(
            settings(
                telegram_mini_app_url="https://example.test",
                mini_app_bind_host="0.0.0.0",
                mini_app_port=8080,
            )
        )
        app.bot_data["state"] = configured_state
        service = MagicMock(spec=MiniAppService)
        with patch.object(tb, "start_mini_app", AsyncMock(return_value=service)) as start:
            self.assertTrue(await tb._configure_mini_app(app))
        start.assert_awaited_once_with(
            db=configured_state.db,
            bot_token="token",
            bot=bot,
            public_url="https://example.test",
            host="0.0.0.0",
            port=8080,
        )
        self.assertIs(app.bot_data["mini_app_service"], service)
        self.assertEqual(bot.set_chat_menu_button.await_args.kwargs["menu_button"].text, "Mis álbumes")

        bot.set_chat_menu_button.side_effect = TimedOut()
        with patch.object(tb, "start_mini_app", AsyncMock(return_value=service)):
            self.assertTrue(await tb._configure_mini_app(app))

    async def test_send_hisopo_collection_without_and_with_mini_app(self) -> None:
        db = MagicMock()
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        db.get_hisopo_collection.return_value = [
            HisopoCollectionEntry("common", 2, "first", "last")
        ]
        message = SimpleNamespace(
            chat=SimpleNamespace(id=-1),
            reply_text=AsyncMock(),
        )
        requester = User(id=1, first_name="Ada", is_bot=False)
        target = User(id=2, first_name="Grace", is_bot=False)

        self.assertTrue(
            await tb._send_hisopo_collection(
                db=db,
                message=message,
                requester=requester,
                target_user=target,
                settings=settings(),
                bot_username="",
            )
        )
        kwargs = message.reply_text.await_args.kwargs
        self.assertIsNone(kwargs["reply_markup"])
        self.assertIn("Grace (2)", message.reply_text.await_args.args[0])

        message.reply_text.reset_mock()
        configured = settings(
            telegram_mini_app_url="https://example.test",
            telegram_mini_app_short_name="hisopos",
        )
        self.assertTrue(
            await tb._send_hisopo_collection(
                db=db,
                message=message,
                requester=requester,
                target_user=target,
                settings=configured,
                bot_username="galerazo_bot",
            )
        )
        button = message.reply_text.await_args.kwargs["reply_markup"].inline_keyboard[0][0]
        self.assertIn("startapp=", button.url)

        message.reply_text.side_effect = TimedOut()
        self.assertFalse(
            await tb._send_hisopo_collection(
                db=db,
                message=message,
                requester=requester,
                target_user=target,
                settings=configured,
                bot_username="galerazo_bot",
            )
        )


if __name__ == "__main__":
    unittest.main()
