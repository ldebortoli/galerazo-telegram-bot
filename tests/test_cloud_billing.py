from __future__ import annotations

import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from galerazo_bot.cloud_billing import (
    ARGENTINA_TIMEZONE,
    MAXIMUM_BYTES_BILLED,
    GoogleCloudBillingAmount,
    GoogleCloudBillingConfig,
    GoogleCloudBillingReader,
    GoogleCloudBillingReport,
    format_google_cloud_billing_report,
    parse_report_time,
)
from galerazo_bot.config import Settings
from galerazo_bot.telegram_bot import (
    _schedule_google_cloud_billing_report,
    _send_google_cloud_billing_report,
)


class FakeQueryJob:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows
        self.timeout: int | None = None

    def result(self, timeout: int) -> list[object]:
        self.timeout = timeout
        return self.rows


class FakeBigQueryClient:
    def __init__(self, rows: list[object]) -> None:
        self.job = FakeQueryJob(rows)
        self.query_text = ""
        self.job_config = None

    def query(self, query: str, job_config: object) -> FakeQueryJob:
        self.query_text = query
        self.job_config = job_config
        return self.job


class FakeJobQueue:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def run_daily(self, callback: object, **kwargs: object) -> None:
        self.calls.append({"callback": callback, **kwargs})


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "telegram_bot_token": "token",
        "telegram_dev_user_ids": frozenset({"1"}),
        "telegram_log_chat_id": "-100123",
        "telegram_announcements_chat_id": None,
        "database_path": SimpleNamespace(),
        "google_sheets_credentials_json_path": None,
        "google_sheets_spreadsheet_id": None,
        "google_sheets_worksheet_name": "Gastos",
        "google_cloud_billing_project_id": None,
        "google_cloud_billing_table": None,
        "google_cloud_billing_report_time": "09:00",
    }
    values.update(overrides)
    return Settings(**values)


class GoogleCloudBillingReaderTests(unittest.IsolatedAsyncioTestCase):
    def test_report_time_uses_argentina_timezone(self) -> None:
        report_time = parse_report_time("09:15")

        self.assertEqual((report_time.hour, report_time.minute), (9, 15))
        self.assertIs(report_time.tzinfo, ARGENTINA_TIMEZONE)

    def test_report_time_rejects_invalid_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "HH:MM"):
            parse_report_time("25:00")

    def test_export_table_rejects_sql_fragments(self) -> None:
        with self.assertRaisesRegex(ValueError, "project.dataset.table"):
            GoogleCloudBillingReader(
                GoogleCloudBillingConfig(
                    query_project_id="bot-fleet-production",
                    export_table="project.dataset.table` WHERE TRUE; --",
                )
            )

    async def test_queries_argentina_invoice_month_with_cost_cap(self) -> None:
        latest_export = datetime(2026, 7, 2, 14, 30, tzinfo=timezone.utc)
        client = FakeBigQueryClient(
            [
                SimpleNamespace(
                    currency="USD",
                    gross_cost=Decimal("1.25"),
                    credits=Decimal("-1.00"),
                    net_cost=Decimal("0.25"),
                    latest_export_time=latest_export,
                )
            ]
        )
        reader = GoogleCloudBillingReader(
            GoogleCloudBillingConfig(
                query_project_id="bot-fleet-production",
                export_table=(
                    "bot-fleet-production.billing_export."
                    "gcp_billing_export_v1_ABCDEF_ABCDEF_ABCDEF"
                ),
            ),
            client_factory=lambda project_id: client,
        )

        report = await reader.get_month_to_date(
            datetime(2026, 7, 1, 2, 0, tzinfo=timezone.utc)
        )

        self.assertEqual(report.invoice_month, "202606")
        self.assertEqual(report.amounts[0].net_cost, Decimal("0.25"))
        self.assertEqual(report.latest_export_time, latest_export)
        self.assertIn("invoice.month = @invoice_month", client.query_text)
        self.assertNotIn("202606", client.query_text)
        self.assertEqual(client.job_config.maximum_bytes_billed, MAXIMUM_BYTES_BILLED)
        self.assertEqual(client.job_config.query_parameters[0].value, "202606")
        self.assertEqual(client.job.timeout, 30)

    async def test_unconfigured_reader_does_not_query(self) -> None:
        reader = GoogleCloudBillingReader(
            GoogleCloudBillingConfig(query_project_id=None, export_table=None)
        )
        with self.assertRaisesRegex(RuntimeError, "no esta configurado"):
            await reader.get_month_to_date()


class GoogleCloudBillingFormattingTests(unittest.TestCase):
    def test_formats_monthly_costs_and_export_freshness(self) -> None:
        report = GoogleCloudBillingReport(
            invoice_month="202607",
            amounts=(
                GoogleCloudBillingAmount(
                    currency="USD",
                    gross_cost=Decimal("1234.5"),
                    credits=Decimal("-1200.25"),
                    net_cost=Decimal("34.25"),
                ),
            ),
            latest_export_time=datetime(2026, 7, 22, 12, 30, tzinfo=timezone.utc),
        )

        text = format_google_cloud_billing_report(report)

        self.assertIn("Periodo: julio de 2026", text)
        self.assertIn("Gasto bruto: USD 1.234,50", text)
        self.assertIn("Creditos: USD -1.200,25", text)
        self.assertIn("Gasto neto: USD 34,25", text)
        self.assertIn("22/07/2026 09:30 (Argentina)", text)
        self.assertIn("puede tener demora", text)

    def test_formats_export_without_current_month_rows(self) -> None:
        text = format_google_cloud_billing_report(
            GoogleCloudBillingReport(
                invoice_month="202607",
                amounts=(),
                latest_export_time=None,
            )
        )

        self.assertIn("Todavia no hay datos exportados", text)
        self.assertNotIn("Gasto neto", text)


class GoogleCloudBillingSchedulingTests(unittest.IsolatedAsyncioTestCase):
    def test_example_environment_keeps_billing_disabled(self) -> None:
        env_values = dict(
            line.split("=", 1)
            for line in (Path(__file__).resolve().parents[1] / ".env.example")
            .read_text(encoding="utf-8")
            .splitlines()
            if line and not line.startswith("#")
        )

        self.assertEqual(env_values["GOOGLE_CLOUD_BILLING_PROJECT_ID"], "")
        self.assertEqual(env_values["GOOGLE_CLOUD_BILLING_TABLE"], "")
        self.assertEqual(env_values["GOOGLE_CLOUD_BILLING_REPORT_TIME"], "09:00")

    def test_does_not_schedule_incomplete_configuration(self) -> None:
        queue = FakeJobQueue()
        application = SimpleNamespace(job_queue=queue)

        scheduled = _schedule_google_cloud_billing_report(
            application,
            make_settings(),
        )

        self.assertFalse(scheduled)
        self.assertEqual(queue.calls, [])

    def test_does_not_query_without_logging_destination(self) -> None:
        queue = FakeJobQueue()
        application = SimpleNamespace(job_queue=queue)

        scheduled = _schedule_google_cloud_billing_report(
            application,
            make_settings(
                telegram_log_chat_id=None,
                google_cloud_billing_project_id="bot-fleet-production",
                google_cloud_billing_table=(
                    "bot-fleet-production.billing_export."
                    "gcp_billing_export_v1_ABCDEF_ABCDEF_ABCDEF"
                ),
            ),
        )

        self.assertFalse(scheduled)
        self.assertEqual(queue.calls, [])

    def test_schedules_one_daily_non_overlapping_job(self) -> None:
        queue = FakeJobQueue()
        application = SimpleNamespace(job_queue=queue)
        settings = make_settings(
            google_cloud_billing_project_id="bot-fleet-production",
            google_cloud_billing_table=(
                "bot-fleet-production.billing_export."
                "gcp_billing_export_v1_ABCDEF_ABCDEF_ABCDEF"
            ),
            google_cloud_billing_report_time="08:45",
        )

        scheduled = _schedule_google_cloud_billing_report(application, settings)

        self.assertTrue(scheduled)
        self.assertEqual(len(queue.calls), 1)
        call = queue.calls[0]
        self.assertEqual(call["name"], "google-cloud-monthly-spend")
        self.assertEqual((call["time"].hour, call["time"].minute), (8, 45))
        self.assertEqual(call["job_kwargs"]["max_instances"], 1)
        self.assertTrue(call["job_kwargs"]["coalesce"])

    async def test_sends_report_to_logging_channel(self) -> None:
        reader = SimpleNamespace(
            get_month_to_date=AsyncMock(
                return_value=GoogleCloudBillingReport(
                    invoice_month="202607",
                    amounts=(),
                    latest_export_time=None,
                )
            )
        )
        bot = SimpleNamespace(send_message=AsyncMock())

        sent = await _send_google_cloud_billing_report(bot, "-100123", reader)

        self.assertTrue(sent)
        self.assertEqual(bot.send_message.await_args.kwargs["chat_id"], -100123)
        self.assertIn(
            "Todavia no hay datos exportados",
            bot.send_message.await_args.kwargs["text"],
        )

    async def test_query_failure_is_reported_without_exception_details(self) -> None:
        reader = SimpleNamespace(
            get_month_to_date=AsyncMock(side_effect=RuntimeError("secret detail"))
        )
        bot = SimpleNamespace(send_message=AsyncMock())

        with patch("galerazo_bot.telegram_bot.logger.exception"):
            sent = await _send_google_cloud_billing_report(bot, "-100123", reader)

        self.assertTrue(sent)
        text = bot.send_message.await_args.kwargs["text"]
        self.assertIn("No pude consultar el gasto", text)
        self.assertNotIn("secret detail", text)


if __name__ == "__main__":
    unittest.main()
