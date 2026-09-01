from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from telegram.error import TimedOut
from telegram.ext import AIORateLimiter, ExtBot
from telegram.request import HTTPXRequest


logger = logging.getLogger(__name__)
TELEGRAM_REQUEST_MAX_ATTEMPTS = 3
TELEGRAM_REQUEST_RETRY_DELAYS_SECONDS = (1.0, 2.0)
TELEGRAM_RATE_LIMIT_MAX_RETRIES = 2
T = TypeVar("T")


async def retry_timed_out(
    operation: Callable[[], Awaitable[T]],
    operation_name: str,
) -> T:
    attempt = 1
    while True:
        try:
            return await operation()
        except TimedOut:
            if attempt >= TELEGRAM_REQUEST_MAX_ATTEMPTS:
                logger.error(
                    "%s fallo con TimedOut despues de %s intentos. Telegram pudo haber "
                    "aceptado una o mas solicitudes sin confirmar la respuesta y la "
                    "operacion puede haberse duplicado.",
                    operation_name,
                    TELEGRAM_REQUEST_MAX_ATTEMPTS,
                    exc_info=True,
                )
                raise

            delay = TELEGRAM_REQUEST_RETRY_DELAYS_SECONDS[attempt - 1]
            logger.warning(
                "%s agoto el timeout en el intento %s/%s; reintentando en %.1f segundos.",
                operation_name,
                attempt,
                TELEGRAM_REQUEST_MAX_ATTEMPTS,
                delay,
            )
            await asyncio.sleep(delay)
            attempt += 1


class RetryingAIORateLimiter(AIORateLimiter):
    """Apply the common timeout retry policy to every rate-limited Bot API call."""

    async def process_request(
        self,
        callback: Callable[..., Awaitable[T]],
        args: Any,
        kwargs: dict[str, Any],
        endpoint: str,
        data: dict[str, Any],
        rate_limit_args: int | None,
    ) -> T:
        async def request() -> T:
            return await super(RetryingAIORateLimiter, self).process_request(
                callback=callback,
                args=args,
                kwargs=kwargs,
                endpoint=endpoint,
                data=data,
                rate_limit_args=rate_limit_args,
            )

        return await retry_timed_out(request, endpoint)


class RetryingExtBot(ExtBot):
    """ExtBot configured with the project-wide Telegram retry policy."""


def build_retrying_ext_bot(token: str, request_timeout_seconds: float) -> RetryingExtBot:
    return RetryingExtBot(
        token=token,
        request=HTTPXRequest(
            connect_timeout=request_timeout_seconds,
            read_timeout=request_timeout_seconds,
            write_timeout=request_timeout_seconds,
            pool_timeout=request_timeout_seconds,
        ),
        get_updates_request=HTTPXRequest(connection_pool_size=1),
        rate_limiter=RetryingAIORateLimiter(max_retries=TELEGRAM_RATE_LIMIT_MAX_RETRIES),
    )
