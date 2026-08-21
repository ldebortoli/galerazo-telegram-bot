from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from telegram.error import RetryAfter, TimedOut
from telegram.ext import AIORateLimiter, ExtBot

from galerazo_bot.telegram_retry import (
    SEND_MESSAGE_RETRY_DELAYS_SECONDS,
    TELEGRAM_RATE_LIMIT_MAX_RETRIES,
    RetryingExtBot,
    build_retrying_ext_bot,
    retry_timed_out,
)


class TelegramRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_immediately_after_first_success(self) -> None:
        operation = AsyncMock(return_value="sent")

        with patch("galerazo_bot.telegram_retry.asyncio.sleep", new=AsyncMock()) as sleep:
            result = await retry_timed_out(operation, "send_message")

        self.assertEqual(result, "sent")
        operation.assert_awaited_once()
        sleep.assert_not_awaited()

    async def test_retries_two_timeouts_and_stops_on_success(self) -> None:
        operation = AsyncMock(side_effect=[TimedOut(), TimedOut(), "sent"])

        with patch("galerazo_bot.telegram_retry.asyncio.sleep", new=AsyncMock()) as sleep:
            result = await retry_timed_out(operation, "send_message")

        self.assertEqual(result, "sent")
        self.assertEqual(operation.await_count, 3)
        self.assertEqual(
            [call.args[0] for call in sleep.await_args_list],
            list(SEND_MESSAGE_RETRY_DELAYS_SECONDS),
        )

    async def test_raises_third_timeout_and_logs_duplicate_risk(self) -> None:
        operation = AsyncMock(side_effect=TimedOut())

        with patch("galerazo_bot.telegram_retry.asyncio.sleep", new=AsyncMock()) as sleep, self.assertLogs(
            "galerazo_bot.telegram_retry",
            level="ERROR",
        ) as captured, self.assertRaises(TimedOut):
            await retry_timed_out(operation, "send_message")

        self.assertEqual(operation.await_count, 3)
        self.assertEqual(sleep.await_count, 2)
        self.assertIn("despues de 3 intentos", "\n".join(captured.output))
        self.assertIn("puede haberse duplicado", "\n".join(captured.output))

    async def test_send_message_does_not_duplicate_global_rate_limit_retries(self) -> None:
        operation = AsyncMock(side_effect=RetryAfter(1))

        with self.assertRaises(RetryAfter):
            await retry_timed_out(operation, "send_message")

        operation.assert_awaited_once()

    async def test_retrying_bot_routes_send_message_through_policy(self) -> None:
        bot = RetryingExtBot("123456:TEST_TOKEN")
        sent = SimpleNamespace(message_id=1)

        with patch.object(ExtBot, "send_message", new=AsyncMock(return_value=sent)) as send:
            result = await bot.send_message(chat_id=1, text="hola")

        self.assertIs(result, sent)
        send.assert_awaited_once_with(chat_id=1, text="hola")

    def test_factory_preserves_normal_request_timeouts(self) -> None:
        bot = build_retrying_ext_bot("123456:TEST_TOKEN", 30)

        self.assertIsInstance(bot, RetryingExtBot)
        self.assertEqual(bot.request.read_timeout, 30)
        self.assertIsInstance(bot.rate_limiter, AIORateLimiter)
        self.assertEqual(bot.rate_limiter._max_retries, TELEGRAM_RATE_LIMIT_MAX_RETRIES)

    async def test_global_rate_limiter_retries_send_photo_three_times_total(self) -> None:
        bot = build_retrying_ext_bot("123456:TEST_TOKEN", 30)
        callback = AsyncMock(
            side_effect=[RetryAfter(1), RetryAfter(2), {"message_id": 1}]
        )

        with patch("telegram.ext._aioratelimiter.asyncio.sleep", new=AsyncMock()) as sleep:
            result = await bot.rate_limiter.process_request(
                callback=callback,
                args=(),
                kwargs={},
                endpoint="sendPhoto",
                data={"chat_id": -1},
                rate_limit_args=None,
            )

        self.assertEqual(result, {"message_id": 1})
        self.assertEqual(callback.await_count, 3)
        self.assertEqual([call.args[0] for call in sleep.await_args_list], [1.1, 2.1])
