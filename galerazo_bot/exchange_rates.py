from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx


CRYPTOYA_BINANCE_USDT_ARS_URL = "https://criptoya.com/api/binance/USDT/ARS/1"
CRYPTOYA_SOURCE = "CriptoYa Binance USDT venta (bid), no P2P"


class ExchangeRateError(RuntimeError):
    """The configured exchange-rate source did not return a usable quote."""


@dataclass(frozen=True)
class ExchangeRateQuote:
    ars_per_usdt: Decimal
    quoted_at: datetime
    source: str = CRYPTOYA_SOURCE


class CriptoYaRateProvider:
    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout_seconds = timeout_seconds

    def binance_usdt_sell_rate(self) -> ExchangeRateQuote:
        try:
            response = httpx.get(
                CRYPTOYA_BINANCE_USDT_ARS_URL,
                timeout=self._timeout_seconds,
                follow_redirects=True,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ExchangeRateError("No pude consultar CriptoYa.") from exc
        return _parse_criptoya_quote(payload)


def _parse_criptoya_quote(payload: Any) -> ExchangeRateQuote:
    if not isinstance(payload, dict):
        raise ExchangeRateError("CriptoYa devolvió una respuesta inválida.")
    try:
        rate = Decimal(str(payload["bid"]))
        timestamp = int(payload["time"])
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise ExchangeRateError("CriptoYa no devolvió la venta de Binance.") from exc
    if not rate.is_finite() or rate <= 0 or timestamp <= 0:
        raise ExchangeRateError("CriptoYa devolvió una cotización inválida.")
    return ExchangeRateQuote(
        ars_per_usdt=rate,
        quoted_at=datetime.fromtimestamp(timestamp, tz=timezone.utc),
    )
