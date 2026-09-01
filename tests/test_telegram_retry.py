from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from telegram.error import RetryAfter, TimedOut

from galerazo_bot.telegram_retry import (
    TELEGRAM_REQUEST_RETRY_DELAYS_SECONDS,
    TELEGRAM_RATE_LIMIT_MAX_RETRIES,
    RetryingAIORateLimiter,
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
            list(TELEGRAM_REQUEST_RETRY_DELAYS_SECONDS),
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

    def test_factory_preserves_normal_request_timeouts(self) -> None:
        bot = build_retrying_ext_bot("123456:TEST_TOKEN", 30)

        self.assertIsInstance(bot, RetryingExtBot)
        self.assertEqual(bot.request.read_timeout, 30)
        self.assertIsInstance(bot.rate_limiter, RetryingAIORateLimiter)
        self.assertEqual(bot.rate_limiter._max_retries, TELEGRAM_RATE_LIMIT_MAX_RETRIES)

    async def test_global_policy_retries_sends_and_edits_three_times_total(self) -> None:
        bot = build_retrying_ext_bot("123456:TEST_TOKEN", 30)
        endpoints = (
            "sendMessage",
            "sendPhoto",
            "sendVideo",
            "sendDocument",
            "editMessageText",
            "editMessageCaption",
            "editMessageMedia",
            "editMessageReplyMarkup",
        )

        for endpoint in endpoints:
            callback = AsyncMock(side_effect=[TimedOut(), TimedOut(), {"ok": True}])
            with self.subTest(endpoint=endpoint), patch(
                "galerazo_bot.telegram_retry.asyncio.sleep", new=AsyncMock()
            ) as sleep:
                result = await bot.rate_limiter.process_request(
                    callback=callback,
                    args=(),
                    kwargs={},
                    endpoint=endpoint,
                    data={"chat_id": -1},
                    rate_limit_args=None,
                )

            self.assertEqual(result, {"ok": True})
            self.assertEqual(callback.await_count, 3)
            self.assertEqual(
                [call.args[0] for call in sleep.await_args_list],
                list(TELEGRAM_REQUEST_RETRY_DELAYS_SECONDS),
            )

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
