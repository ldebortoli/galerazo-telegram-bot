from __future__ import annotations

import asyncio
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, time, timezone
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from google.cloud import bigquery


ARGENTINA_TIMEZONE = ZoneInfo("America/Argentina/Buenos_Aires")
MAXIMUM_BYTES_BILLED = 100 * 1024 * 1024
QUERY_TIMEOUT_SECONDS = 30
_TABLE_PATTERN = re.compile(
    r"^[a-z][a-z0-9-]{4,61}[a-z0-9]\.[A-Za-z_][A-Za-z0-9_]{0,1023}\."
    r"[A-Za-z_][A-Za-z0-9_]{0,1023}$"
)
_MONTH_NAMES_ES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


@dataclass(frozen=True)
class GoogleCloudBillingConfig:
    query_project_id: str | None
    export_table: str | None

    @property
    def is_configured(self) -> bool:
        return bool(self.query_project_id and self.export_table)


@dataclass(frozen=True)
class GoogleCloudBillingAmount:
    currency: str
    gross_cost: Decimal
    credits: Decimal
    net_cost: Decimal


@dataclass(frozen=True)
class GoogleCloudBillingReport:
    invoice_month: str
    amounts: tuple[GoogleCloudBillingAmount, ...]
    latest_export_time: datetime | None


def parse_report_time(value: str) -> time:
    try:
        parsed = datetime.strptime(value.strip(), "%H:%M")
    except ValueError as exc:
        raise ValueError("GOOGLE_CLOUD_BILLING_REPORT_TIME debe usar HH:MM") from exc
    return time(parsed.hour, parsed.minute, tzinfo=ARGENTINA_TIMEZONE)


class GoogleCloudBillingReader:
    def __init__(
        self,
        config: GoogleCloudBillingConfig,
        client_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self.config = config
        self._client_factory = client_factory or _create_bigquery_client
        if config.export_table and not _TABLE_PATTERN.fullmatch(config.export_table):
            raise ValueError(
                "GOOGLE_CLOUD_BILLING_TABLE debe usar project.dataset.table con identificadores validos"
            )

    async def get_month_to_date(
        self,
        now: datetime | None = None,
    ) -> GoogleCloudBillingReport:
        if not self.config.is_configured:
            raise RuntimeError("El reporte de Google Cloud Billing no esta configurado")
        report_time = now or datetime.now(ARGENTINA_TIMEZONE)
        invoice_month = report_time.astimezone(ARGENTINA_TIMEZONE).strftime("%Y%m")
        return await asyncio.to_thread(self._query, invoice_month)

    def _query(self, invoice_month: str) -> GoogleCloudBillingReport:
        project_id = self.config.query_project_id
        export_table = self.config.export_table
        if not project_id or not export_table:
            raise RuntimeError("El reporte de Google Cloud Billing no esta configurado")

        client = self._client_factory(project_id)
        query = f"""
            WITH line_items AS (
              SELECT
                currency,
                CAST(cost AS NUMERIC) AS cost,
                IFNULL(
                  (SELECT SUM(CAST(credit.amount AS NUMERIC)) FROM UNNEST(credits) AS credit),
                  NUMERIC '0'
                ) AS credits,
                export_time
              FROM `{export_table}`
              WHERE invoice.month = @invoice_month
            )
            SELECT
              currency,
              SUM(cost) AS gross_cost,
              SUM(credits) AS credits,
              SUM(cost) + SUM(credits) AS net_cost,
              MAX(export_time) AS latest_export_time
            FROM line_items
            GROUP BY currency
            ORDER BY currency
        """
        job_config = bigquery.QueryJobConfig(
            maximum_bytes_billed=MAXIMUM_BYTES_BILLED,
            query_parameters=[
                bigquery.ScalarQueryParameter("invoice_month", "STRING", invoice_month)
            ],
            use_query_cache=True,
        )
        rows = client.query(query, job_config=job_config).result(
            timeout=QUERY_TIMEOUT_SECONDS
        )
        return _build_report(invoice_month, rows)


def _create_bigquery_client(project_id: str) -> bigquery.Client:
    return bigquery.Client(project=project_id)


def _build_report(
    invoice_month: str,
    rows: Iterable[Any],
) -> GoogleCloudBillingReport:
    amounts: list[GoogleCloudBillingAmount] = []
    latest_export_time: datetime | None = None
    for row in rows:
        amounts.append(
            GoogleCloudBillingAmount(
                currency=str(row.currency),
                gross_cost=_as_decimal(row.gross_cost),
                credits=_as_decimal(row.credits),
                net_cost=_as_decimal(row.net_cost),
            )
        )
        row_export_time = row.latest_export_time
        if row_export_time is not None and (
            latest_export_time is None or row_export_time > latest_export_time
        ):
            latest_export_time = row_export_time
    return GoogleCloudBillingReport(
        invoice_month=invoice_month,
        amounts=tuple(amounts),
        latest_export_time=latest_export_time,
    )


def _as_decimal(value: object) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def format_google_cloud_billing_report(report: GoogleCloudBillingReport) -> str:
    year = int(report.invoice_month[:4])
    month = int(report.invoice_month[4:])
    lines = [
        "Google Cloud - gasto mensual",
        f"Periodo: {_MONTH_NAMES_ES[month - 1]} de {year}",
    ]
    if not report.amounts:
        lines.extend(
            (
                "Todavia no hay datos exportados para este periodo.",
                "La exportacion de Billing puede tener una demora superior a 24 horas.",
            )
        )
        return "\n".join(lines)

    for amount in report.amounts:
        lines.extend(
            (
                f"Gasto bruto: {amount.currency} {_format_decimal(amount.gross_cost)}",
                f"Creditos: {amount.currency} {_format_decimal(amount.credits)}",
                f"Gasto neto: {amount.currency} {_format_decimal(amount.net_cost)}",
            )
        )
    if report.latest_export_time is not None:
        export_time = report.latest_export_time
        if export_time.tzinfo is None:
            export_time = export_time.replace(tzinfo=timezone.utc)
        local_time = export_time.astimezone(ARGENTINA_TIMEZONE)
        lines.append(f"Datos actualizados: {local_time:%d/%m/%Y %H:%M} (Argentina)")
    lines.append("La exportacion de Billing puede tener demora.")
    return "\n".join(lines)


def _format_decimal(value: Decimal) -> str:
    formatted = f"{value:,.2f}"
    return formatted.replace(",", "_").replace(".", ",").replace("_", ".")
