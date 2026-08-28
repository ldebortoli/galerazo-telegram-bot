from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
from gspread.exceptions import WorksheetNotFound

from galerazo_bot import exchange_rates, expenses, google_sheets
from galerazo_bot.database import Database, Expense
from galerazo_bot.expenses import ExpenseMovement


def make_expense(**overrides) -> Expense:
    values = dict(
        expense_id=1,
        chat_id="1",
        user_id="1",
        username=None,
        display_name="Lucas",
        amount_cents=12_345,
        currency="ARS",
        payment_method="Efectivo",
        source="Supermercado",
        description="compras",
        sheet_status="pending",
        sheet_error=None,
        created_at="2026-08-28 12:00:00",
        synced_at=None,
        occurred_on="2026-08-28",
        movement_type="purchase",
        category="Supermercado",
        author="Lucas",
        installments=0,
        usd_rate="1600.50",
        usd_rate_source="CriptoYa",
        usd_rate_quoted_at="2026-08-28T12:00:00+00:00",
        include_cashflow=True,
        opens_cashflow_month=True,
        purchase_sheet_row=None,
        cashflow_sheet_name=None,
        cashflow_sheet_row=None,
    )
    values.update(overrides)
    return Expense(**values)


class ExpenseParsingTests(unittest.TestCase):
    def test_resolvers_and_purchase_variants(self) -> None:
        self.assertEqual(expenses.resolve_payment_method("EFECTIVO").label, "Efectivo")
        self.assertIsNone(expenses.resolve_payment_method("inventado"))
        self.assertEqual(expenses.resolve_category("pan"), "Panadería")
        self.assertIsNone(expenses.resolve_category("inventada"))

        immediate = expenses.parse_expense_command_args(
            "18500 | sup | j | mpl | 28/08/2026 | @1600,50 | comida",
            today=date(2026, 8, 28),
        )
        self.assertEqual(immediate.author, "Jo")
        self.assertEqual(immediate.usd_rate_override, Decimal("1600.5"))
        self.assertTrue(immediate.include_cashflow)
        self.assertEqual(immediate.installments, 0)

        credit = expenses.parse_expense_command_args(
            "120000 | ropa | vgl | 3c | campera",
            today=date(2026, 8, 28),
        )
        self.assertFalse(credit.include_cashflow)
        self.assertEqual(credit.installments, 3)
        default_credit = expenses.parse_expense_command_args(
            "120000 | ropa | vgl | campera",
            today=date(2026, 8, 28),
        )
        self.assertEqual(default_credit.installments, 1)

        usd = expenses.parse_expense_command_args(
            "17.22usd | otro | payol | hosting",
            today=date(2026, 8, 28),
        )
        self.assertEqual((usd.currency, usd.installments), ("USD", 1))

    def test_invalid_purchase_and_modifier_variants(self) -> None:
        invalid = (
            "1 | noexiste | ef | x",
            "1 | otro | noexiste | x",
            "1usd | otro | ef | 2c | x",
            "1usd | otro | ef | @2 | x",
            "1 | otro | vgl | 0c | x",
            "1 | otro | ef | 2c | x",
            "1 | otro | ef | ef | x",
            "1 | otro | j | j | ef | x",
            "1 | otro | 28/08 | 29/08 | ef | x",
            "1 | otro | 2c | 3c | vgl | x",
            "1 | otro | @1 | @2 | ef | x",
            "0 | otro | ef | x",
            "-2 | otro | ef | x",
        )
        for raw in invalid:
            with self.subTest(raw=raw):
                self.assertIsNone(
                    expenses.parse_expense_command_args(raw, today=date(2026, 8, 28))
                )
        self.assertIsNone(expenses._parse_modifiers([], "Lucas", date(2026, 8, 28)))
        self.assertIsNone(expenses._parse_rate("2"))
        self.assertIsNone(expenses._parse_rate("@x"))
        self.assertIsNone(expenses._parse_rate("@0"))
        self.assertIsNone(expenses._parse_installments("c"))

    def test_statement_dates_and_help(self) -> None:
        statement = expenses.parse_card_statement_command_args(
            "250000 | a | sgl | 27-08 | Visa y Master",
            today=date(2026, 8, 28),
        )
        self.assertEqual(statement.category, expenses.CARD_STATEMENT_CATEGORY)
        self.assertEqual(statement.author, "Ambos")
        self.assertFalse(statement.opens_cashflow_month)
        self.assertEqual(statement.occurred_on, date(2026, 8, 27))

        for raw in (
            "",
            "1 | ef | ",
            "x | ef | resumen",
            "1 | x | resumen",
            "1 | vgl | resumen",
            "1usd | ef | @2 | resumen",
        ):
            with self.subTest(raw=raw):
                self.assertIsNone(
                    expenses.parse_card_statement_command_args(raw, today=date(2026, 8, 28))
                )
        self.assertEqual(
            expenses.parse_closing_date("02/03", date(2026, 8, 28)), date(2026, 3, 2)
        )
        self.assertEqual(
            expenses.parse_closing_date("02-03-2027", date(2026, 8, 28)), date(2027, 3, 2)
        )
        self.assertIsNone(expenses.parse_closing_date("31/02", date(2026, 8, 28)))
        self.assertIn("Pago de resumen", expenses.expense_help_text())


class ExchangeRateTests(unittest.TestCase):
    def test_provider_uses_binance_bid(self) -> None:
        response = MagicMock()
        response.json.return_value = {"ask": 1700, "bid": 1605.8, "time": 1787904000}
        with patch("galerazo_bot.exchange_rates.httpx.get", return_value=response) as get:
            quote = exchange_rates.CriptoYaRateProvider(3).binance_usdt_sell_rate()
        self.assertEqual(quote.ars_per_usdt, Decimal("1605.8"))
        self.assertIn("no P2P", quote.source)
        get.assert_called_once_with(
            exchange_rates.CRYPTOYA_BINANCE_USDT_ARS_URL,
            timeout=3,
            follow_redirects=True,
        )
        response.raise_for_status.assert_called_once()

    def test_provider_and_payload_failures(self) -> None:
        with patch(
            "galerazo_bot.exchange_rates.httpx.get",
            side_effect=httpx.ConnectError("offline"),
        ):
            with self.assertRaises(exchange_rates.ExchangeRateError):
                exchange_rates.CriptoYaRateProvider().binance_usdt_sell_rate()
        response = MagicMock()
        response.json.side_effect = ValueError("bad json")
        with patch("galerazo_bot.exchange_rates.httpx.get", return_value=response):
            with self.assertRaises(exchange_rates.ExchangeRateError):
                exchange_rates.CriptoYaRateProvider().binance_usdt_sell_rate()
        for payload in (
            [],
            {},
            {"bid": "x", "time": 1},
            {"bid": 1, "time": "x"},
            {"bid": 0, "time": 1},
            {"bid": "NaN", "time": 1},
            {"bid": 1, "time": 0},
        ):
            with self.subTest(payload=payload), self.assertRaises(exchange_rates.ExchangeRateError):
                exchange_rates._parse_criptoya_quote(payload)


class SheetHelperTests(unittest.TestCase):
    def test_request_builders_and_dates(self) -> None:
        self.assertEqual(google_sheets._string_value("x")["userEnteredValue"]["stringValue"], "x")
        self.assertEqual(google_sheets._number_value(Decimal("1.2"))["userEnteredValue"]["numberValue"], 1.2)
        self.assertEqual(google_sheets._formula_value("=A1")["userEnteredValue"]["formulaValue"], "=A1")
        self.assertEqual(google_sheets._google_date_number(date(1899, 12, 30)), 0)
        self.assertTrue(google_sheets._same_date("28/08/2026", date(2026, 8, 28)))
        self.assertTrue(google_sheets._same_date("2026-08-28", date(2026, 8, 28)))
        self.assertFalse(google_sheets._same_date("bad", date(2026, 8, 28)))

        row = google_sheets._row_update_request(7, 2, 3, [google_sheets._string_value("x")])
        self.assertEqual(row["updateCells"]["range"]["startColumnIndex"], 2)
        self.assertEqual(
            google_sheets._single_cell_request(7, 2, 3, google_sheets._string_value("x")), row
        )
        clear = google_sheets._clear_values_request(7, 2, 4, 0, 5)
        self.assertEqual(clear["repeatCell"]["range"]["endRowIndex"], 3)
        copy = google_sheets._copy_paste_request(7, 1, 3, 0, 5, 4, 6, "PASTE_NORMAL", destination_sheet_id=8)
        self.assertEqual(copy["copyPaste"]["destination"]["sheetId"], 8)
        same_sheet = google_sheets._copy_paste_request(7, 1, 3, 0, 5, 4, 6, "PASTE_NORMAL")
        self.assertEqual(same_sheet["copyPaste"]["destination"]["sheetId"], 7)

    def test_purchase_and_cashflow_requests(self) -> None:
        worksheet = SimpleNamespace(id=9)
        ars = make_expense()
        purchase = google_sheets._purchase_requests(worksheet, 14, ars)
        values = purchase[1]["updateCells"]["rows"][0]["values"]
        self.assertEqual(len(values), 13)
        self.assertIn("MINIFS", values[10]["userEnteredValue"]["formulaValue"])
        cash = google_sheets._cashflow_requests(worksheet, 20, ars)
        self.assertIn("D20/E20", cash[0]["updateCells"]["rows"][0]["values"][5]["userEnteredValue"]["formulaValue"])

        usd = make_expense(currency="USD", amount_cents=1722, installments=1, usd_rate=None)
        usd_values = google_sheets._purchase_requests(worksheet, 15, usd)[1]["updateCells"]["rows"][0]["values"]
        self.assertEqual(usd_values[5]["userEnteredValue"]["stringValue"], "----")
        self.assertEqual(usd_values[8]["userEnteredValue"]["numberValue"], 1.0)
        usd_cash = google_sheets._cashflow_requests(worksheet, 21, usd)
        self.assertEqual(
            usd_cash[0]["updateCells"]["rows"][0]["values"][3]["userEnteredValue"]["stringValue"],
            "----",
        )
        with self.assertRaises(google_sheets.SheetStructureError):
            google_sheets._purchase_requests(worksheet, 14, replace(ars, usd_rate=None))
        with self.assertRaises(google_sheets.SheetStructureError):
            google_sheets._cashflow_requests(worksheet, 20, replace(ars, usd_rate=None))

    def test_rows_month_blocks_and_new_month(self) -> None:
        worksheet = MagicMock(id=3, row_count=20)
        worksheet.col_values.return_value = ["header"] * 13 + ["used", "", "later"]
        self.assertEqual(google_sheets._next_purchase_row(worksheet), 17)
        worksheet.col_values.return_value = ["header"] * 20
        worksheet.row_count = 20
        self.assertEqual(google_sheets._next_purchase_row(worksheet), 21)
        worksheet.add_rows.assert_called_once()
        worksheet.reset_mock()
        worksheet.col_values.return_value = ["header"] * 20
        worksheet.row_count = 25
        self.assertEqual(google_sheets._next_purchase_row(worksheet), 21)
        worksheet.add_rows.assert_not_called()

        values = [[], [], ["ENERO", "", "x"], [], ["", "", "=x"], ["", "", "=x"], ["FEBRERO"], [], ["", "", "=x"], []]
        annual = MagicMock(id=4, row_count=len(values))
        annual.get.return_value = values
        blocks = google_sheets._find_month_blocks(annual)
        self.assertEqual(blocks[1], google_sheets._MonthBlock(3, 5, 6))
        self.assertEqual(blocks[2], google_sheets._MonthBlock(7, 9, 9))
        self.assertEqual(google_sheets._find_month_block(annual, 2), blocks[2])
        self.assertIsNone(google_sheets._find_month_block(annual, 3))
        self.assertEqual(google_sheets._last_reserved_formula_row([[], []], 2), 58)

        annual.row_count = 10
        block, requests = google_sheets._new_month_requests(annual, 3)
        self.assertEqual(block.label_row, 10)
        self.assertEqual(len(requests), 3)
        annual.add_rows.assert_called_once()
        annual.reset_mock()
        annual.row_count = 100
        annual.get.return_value = values
        google_sheets._new_month_requests(annual, 3)
        annual.add_rows.assert_not_called()
        empty = MagicMock(row_count=1)
        empty.get.return_value = [[]]
        with self.assertRaisesRegex(google_sheets.SheetStructureError, "bloques"):
            google_sheets._new_month_requests(empty, 1)
        with self.assertRaisesRegex(google_sheets.SheetStructureError, "orden"):
            google_sheets._new_month_requests(annual, 5)

        cash = MagicMock()
        cash.get.return_value = [["used"], [], ["later"], []]
        self.assertEqual(google_sheets._next_cashflow_row(cash, google_sheets._MonthBlock(1, 3, 6)), 6)
        cash.get.return_value = [[], [], []]
        self.assertEqual(google_sheets._next_cashflow_row(cash, google_sheets._MonthBlock(1, 3, 5)), 3)
        cash.get.return_value = [["1"], ["2"], ["3"]]
        with self.assertRaisesRegex(google_sheets.SheetStructureError, "filas libres"):
            google_sheets._next_cashflow_row(cash, google_sheets._MonthBlock(1, 3, 5))

        cash.get.return_value = [[]]
        self.assertTrue(google_sheets._cell_is_empty(cash, 3, "A"))
        cash.get.return_value = [["occupied"]]
        self.assertFalse(google_sheets._cell_is_empty(cash, 3, "A"))


class SheetWriterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.key = Path(self.temp.name) / "key.json"
        self.key.write_text("{}", encoding="utf-8")
        self.writer = google_sheets.GoogleSheetsExpenseWriter(
            google_sheets.GoogleSheetsConfig(self.key, "sheet")
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_add_closing_paths(self) -> None:
        missing = google_sheets.GoogleSheetsExpenseWriter(
            google_sheets.GoogleSheetsConfig(None, None)
        )
        self.assertFalse(missing.add_card_closing(date(2026, 8, 28)).configured)
        self.key.unlink()
        self.assertEqual(self.writer.add_card_closing(date(2026, 8, 28)).error, "sheet_not_ready")
        self.key.write_text("{}", encoding="utf-8")

        worksheet = MagicMock(id=2)
        worksheet.get.return_value = [[]]
        spreadsheet = MagicMock()
        with patch.object(self.writer, "_open_spreadsheet", return_value=spreadsheet), patch.object(
            self.writer, "_required_worksheet", return_value=worksheet
        ):
            worksheet.col_values.return_value = [""] * 13 + ["28/08/2026"]
            self.assertTrue(self.writer.add_card_closing(date(2026, 8, 28)).duplicate)
            worksheet.col_values.return_value = [""] * 14
            added = self.writer.add_card_closing(date(2026, 8, 29))
            self.assertTrue(added.added)
            self.assertEqual(added.row_number, 15)
            worksheet.col_values.return_value = []
            self.assertEqual(self.writer.add_card_closing(date(2026, 8, 30)).row_number, 14)

            worksheet.col_values.side_effect = [
                [""] * 14,
                [""] * 15,
            ]
            with patch.object(
                google_sheets,
                "_cell_is_empty",
                side_effect=[False, True],
            ):
                retried = self.writer.add_card_closing(date(2026, 9, 1))
            self.assertEqual(retried.row_number, 16)

            worksheet.col_values.side_effect = [
                [],
                [""] * 13 + ["02/09/2026"],
            ]
            with patch.object(google_sheets, "_cell_is_empty", return_value=False):
                duplicate = self.writer.add_card_closing(date(2026, 9, 2))
            self.assertTrue(duplicate.duplicate)

            worksheet.col_values.side_effect = None
            worksheet.col_values.return_value = []
            with patch.object(google_sheets, "_cell_is_empty", return_value=False):
                occupied = self.writer.add_card_closing(date(2026, 9, 3))
            self.assertEqual(occupied.error, "sheet_target_cell_occupied")
        with patch.object(self.writer, "_open_spreadsheet", side_effect=RuntimeError("api")):
            self.assertEqual(self.writer.add_card_closing(date(2026, 8, 31)).error, "api")

    def test_sheet_resolution_and_open(self) -> None:
        fake_gspread = MagicMock()
        with patch.object(google_sheets, "gspread", fake_gspread):
            self.writer._open_spreadsheet()
        fake_gspread.service_account.assert_called_once_with(filename=str(self.key))
        spreadsheet = MagicMock()
        spreadsheet.worksheet.side_effect = WorksheetNotFound("x")
        self.assertIsNone(self.writer._worksheet_or_none(spreadsheet, "x"))
        with self.assertRaises(google_sheets.SheetStructureError):
            self.writer._required_worksheet(spreadsheet, "x")

    def test_write_expense_flows(self) -> None:
        purchases = MagicMock(id=1, row_count=6000)
        purchases.col_values.return_value = ["x"] * 13 + [""]
        purchases.get.return_value = [[]]
        august_values = [[] for _ in range(70)]
        august_values[0] = ["AGOSTO"]
        for index in range(2, 59):
            august_values[index] = ["", "", "=x"]
        annual = MagicMock(id=2, row_count=70)

        def annual_get(range_name, **_kwargs):
            if range_name.startswith("D1:F"):
                return august_values
            return [[]]

        annual.get.side_effect = annual_get
        spreadsheet = MagicMock()
        spreadsheet.worksheet.side_effect = lambda name: {
            "Gastos y compras": purchases,
            "Gastos 2026": annual,
        }[name]
        card = make_expense(include_cashflow=False, opens_cashflow_month=False)
        result = self.writer._write_expense(spreadsheet, card)
        self.assertTrue(result.success)
        self.assertEqual(result.purchase_sheet_row, 14)

        statement = make_expense(
            movement_type="card_statement",
            category="Pago resumen tarjetas",
            include_cashflow=True,
            opens_cashflow_month=False,
            purchase_sheet_row=None,
        )
        result = self.writer._write_expense(spreadsheet, statement)
        self.assertTrue(result.success)
        self.assertEqual(result.cashflow_sheet_row, 3)
        statement_request = spreadsheet.batch_update.call_args.args[0]["requests"][-1]
        statement_description = statement_request["updateCells"]["rows"][0]["values"][1]
        self.assertIn(
            "Pago resumen tarjetas:",
            statement_description["userEnteredValue"]["stringValue"],
        )

        missing_spreadsheet = MagicMock()
        missing_spreadsheet.worksheet.side_effect = WorksheetNotFound("missing")
        result = self.writer._write_expense(missing_spreadsheet, statement)
        self.assertEqual(result.error, "cashflow_month_not_open")
        january = MagicMock(id=3, row_count=70)
        january.get.return_value = [["ENERO"], [], ["", "", "=x"]]
        missing_month_sheet = MagicMock()
        missing_month_sheet.worksheet.return_value = january
        result = self.writer._write_expense(missing_month_sheet, statement)
        self.assertEqual(result.error, "cashflow_month_not_open")

        no_target = replace(card, movement_type="ignored")
        with self.assertRaises(google_sheets.SheetStructureError):
            self.writer._write_expense(spreadsheet, no_target)

        spreadsheet.batch_update.side_effect = RuntimeError("batch")
        failed = self.writer._write_expense(spreadsheet, card)
        self.assertEqual((failed.error, failed.purchase_sheet_row), ("batch", 14))

    def test_write_never_overwrites_an_occupied_row(self) -> None:
        purchases = MagicMock(id=1, row_count=6000)
        spreadsheet = MagicMock()
        spreadsheet.worksheet.return_value = purchases
        expense = make_expense(include_cashflow=False, opens_cashflow_month=False)

        with patch.object(google_sheets, "_next_purchase_row", side_effect=[14, 15]), patch.object(
            google_sheets,
            "_cell_is_empty",
            side_effect=[False, True],
        ):
            result = self.writer._write_expense(spreadsheet, expense)
        self.assertTrue(result.success)
        self.assertEqual(result.purchase_sheet_row, 15)
        requests = spreadsheet.batch_update.call_args.args[0]["requests"]
        self.assertEqual(requests[-1]["updateCells"]["range"]["startRowIndex"], 14)

        spreadsheet.reset_mock()
        stored = replace(expense, purchase_sheet_row=14)
        with patch.object(google_sheets, "_cell_is_empty", return_value=False):
            result = self.writer._write_expense(spreadsheet, stored)
        self.assertEqual(result.error, "sheet_target_row_occupied")
        self.assertEqual(result.purchase_sheet_row, 14)
        spreadsheet.batch_update.assert_not_called()

        spreadsheet.reset_mock()
        with patch.object(google_sheets, "_next_purchase_row", return_value=14), patch.object(
            google_sheets,
            "_cell_is_empty",
            return_value=False,
        ):
            result = self.writer._write_expense(spreadsheet, expense)
        self.assertEqual(result.error, "sheet_target_row_occupied")
        self.assertIsNone(result.purchase_sheet_row)
        spreadsheet.batch_update.assert_not_called()

    def test_missing_month_creation_and_missing_year(self) -> None:
        purchases = MagicMock(id=1, row_count=6000)
        purchases.col_values.return_value = ["x"] * 13 + [""]
        purchases.get.return_value = [[]]
        july_values = [["JULIO"], [], ["", "", "=x"], ["", "", "=x"], []]
        annual = MagicMock(id=2, row_count=5)

        def annual_get(range_name, **_kwargs):
            if range_name.startswith("D1:F"):
                return july_values
            return [[]]

        annual.get.side_effect = annual_get
        spreadsheet = MagicMock()
        spreadsheet.worksheet.side_effect = lambda name: purchases if name == "Gastos y compras" else annual
        created = self.writer._write_expense(spreadsheet, make_expense())
        self.assertTrue(created.month_created)

        missing = MagicMock()

        def missing_sheet(name):
            if name == "Gastos y compras":
                return purchases
            raise WorksheetNotFound(name)

        missing.worksheet.side_effect = missing_sheet
        created_year = MagicMock(id=4, row_count=70)
        created_year.get.side_effect = lambda range_name, **_kwargs: (
            [["AGOSTO"], [], ["", "", "=x"]]
            if range_name.startswith("D1:F")
            else [[]]
        )
        with patch.object(self.writer, "_create_year_worksheet", return_value=created_year) as create:
            result = self.writer._write_expense(missing, make_expense())
        self.assertTrue(result.month_created)
        create.assert_called_once()

    def test_create_year_success_and_rollback(self) -> None:
        previous = MagicMock(id=1)
        new = MagicMock(id=2)
        spreadsheet = MagicMock()
        spreadsheet.add_worksheet.return_value = new
        with patch.object(self.writer, "_required_worksheet", return_value=previous), patch.object(
            google_sheets, "_find_month_block", return_value=google_sheets._MonthBlock(1, 3, 59)
        ):
            self.assertIs(self.writer._create_year_worksheet(spreadsheet, 2027, "Gastos 2027"), new)
            spreadsheet.batch_update.side_effect = RuntimeError("api")
            with self.assertRaisesRegex(RuntimeError, "api"):
                self.writer._create_year_worksheet(spreadsheet, 2027, "Gastos 2027")
            spreadsheet.del_worksheet.assert_called_with(new)
        with patch.object(self.writer, "_required_worksheet", return_value=previous), patch.object(
            google_sheets, "_find_month_block", return_value=None
        ):
            with self.assertRaisesRegex(google_sheets.SheetStructureError, "ENERO"):
                self.writer._create_year_worksheet(spreadsheet, 2027, "Gastos 2027")

    def test_public_write_catches_external_failure(self) -> None:
        expense = make_expense(purchase_sheet_row=42, cashflow_sheet_name="Gastos 2026", cashflow_sheet_row=8)
        with patch.object(self.writer, "_open_spreadsheet", side_effect=RuntimeError("offline")):
            result = self.writer.write_expense(expense)
        self.assertEqual(
            (result.error, result.purchase_sheet_row, result.cashflow_sheet_row),
            ("offline", 42, 8),
        )


class ExpenseDatabaseTests(unittest.TestCase):
    def test_new_fields_global_queries_and_sheet_locations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "db.sqlite3")
            db.register_chat("1", "private")
            expense = db.add_expense(
                "1",
                "1",
                100,
                "ARS",
                "Efectivo",
                "Supermercado",
                "pan",
                occurred_on="2026-08-28",
                category="Supermercado",
                author="Jo",
                usd_rate="1600",
                include_cashflow=True,
                opens_cashflow_month=True,
            )
            self.assertEqual(expense.author, "Jo")
            self.assertEqual(len(db.list_recent_expenses(None)), 1)
            self.assertEqual(len(db.list_recent_expenses("1")), 1)
            self.assertEqual(len(db.list_pending_expenses(None)), 1)
            self.assertEqual(len(db.list_pending_expenses("1")), 1)
            self.assertEqual(db.count_pending_expenses(None), 1)
            self.assertEqual(db.count_pending_expenses("1"), 1)
            db.mark_expense_failed(expense.expense_id, "api", 20, "Gastos 2026", 30)
            pending = db.list_pending_expenses(None)[0]
            self.assertEqual((pending.purchase_sheet_row, pending.cashflow_sheet_row), (20, 30))
            db.mark_expense_synced(expense.expense_id, 20, "Gastos 2026", 30)
            self.assertEqual(db.count_pending_expenses(None), 0)

    def test_legacy_expense_migration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.sqlite3"
            db = Database(path)
            db.register_chat("1", "private")
            db.get_or_create_user("1")
            with db._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO expenses (
                        chat_id, user_id, amount_cents, currency, payment_method,
                        source, description, occurred_on, category
                    ) VALUES ('1', '1', 1, 'ARS', 'Efectivo', 'Farmacia', 'x', '', 'Otros')
                    """
                )
            Database(path)
            migrated = db.list_recent_expenses(None)[0]
            self.assertTrue(migrated.occurred_on)
            self.assertEqual(migrated.category, "Farmacia")
