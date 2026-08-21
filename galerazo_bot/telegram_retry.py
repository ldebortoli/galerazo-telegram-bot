from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any, TypeVar

from telegram import Message
from telegram.error import RetryAfter, TimedOut
from telegram.ext import ExtBot
from telegram.request import HTTPXRequest


logger = logging.getLogger(__name__)
SEND_MESSAGE_MAX_ATTEMPTS = 3
SEND_MESSAGE_RETRY_DELAYS_SECONDS = (1.0, 2.0)
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
            if attempt >= SEND_MESSAGE_MAX_ATTEMPTS:
                logger.error(
                    "%s fallo con TimedOut despues de %s intentos. Telegram pudo haber "
                    "aceptado uno o mas envios sin confirmar la respuesta y el mensaje "
                    "puede haberse duplicado.",
                    operation_name,
                    SEND_MESSAGE_MAX_ATTEMPTS,
                    exc_info=True,
                )
                raise

            delay = SEND_MESSAGE_RETRY_DELAYS_SECONDS[attempt - 1]
            logger.warning(
                "%s agoto el timeout en el intento %s/%s; reintentando en %.1f segundos.",
                operation_name,
                attempt,
                SEND_MESSAGE_MAX_ATTEMPTS,
                delay,
            )
            await asyncio.sleep(delay)
            attempt += 1
        except RetryAfter as exc:
            if attempt >= SEND_MESSAGE_MAX_ATTEMPTS:
                logger.error(
                    "%s siguio limitado por Telegram despues de %s intentos.",
                    operation_name,
                    SEND_MESSAGE_MAX_ATTEMPTS,
                    exc_info=True,
                )
                raise

            retry_after = exc.retry_after
            delay = (
                retry_after.total_seconds()
                if isinstance(retry_after, timedelta)
                else float(retry_after)
            )
            logger.warning(
                "%s fue limitado por Telegram en el intento %s/%s; "
                "reintentando en %.1f segundos.",
                operation_name,
                attempt,
                SEND_MESSAGE_MAX_ATTEMPTS,
                delay,
            )
            await asyncio.sleep(delay)
            attempt += 1


class RetryingExtBot(ExtBot):
    async def send_message(self, *args: Any, **kwargs: Any) -> Message:
        async def send() -> Message:
            return await super(RetryingExtBot, self).send_message(*args, **kwargs)

        return await retry_timed_out(send, "send_message")


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
    )
