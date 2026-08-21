from __future__ import annotations

import io
import json
import runpy
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from google.cloud import bigquery

from galerazo_bot import chat_config, cli, cloud_billing, commands, config, deploy_backup
from galerazo_bot import expenses, google_sheets, healthcheck, integration_status, logging_utils
from galerazo_bot import pagination, roles, runtime, user_display
from galerazo_bot.command_handlers import help as help_handler
from galerazo_bot.command_handlers import nivel, ruletarusa
from galerazo_bot.database import Database, RussianRouletteShot, User
from galerazo_bot.i18n import TRANSLATIONS
from galerazo_bot.roles import CommandContext, RussianRouletteHitResult, UserLevel


def make_context(**overrides) -> CommandContext:
    base = CommandContext("1", "-1", "group", UserLevel.COMMON, "/x", "")
    return replace(base, **overrides)


class MenuAndPaginationCompleteTests(unittest.TestCase):
    def test_chat_config_helpers_and_fallback_label(self) -> None:
        main = chat_config.build_main_menu("es")
        self.assertEqual(main.inline_keyboard[-1][0].callback_data, "config:close")
        language = chat_config.build_language_menu("es")
        self.assertTrue(language.inline_keyboard[0][0].text.startswith("["))
        groups = chat_config.build_command_groups_menu("en")
        self.assertEqual(groups.inline_keyboard[-1][1].callback_data, "config:close")
        enabled = chat_config.build_command_group_menu("galeraza", True, "es")
        disabled = chat_config.build_command_group_menu("galeraza", False, "es")
        self.assertTrue(enabled.inline_keyboard[0][0].text.startswith("["))
        self.assertTrue(disabled.inline_keyboard[0][1].text.startswith("["))
        self.assertEqual(chat_config.command_group_label("galeraza", "es"), "Galeraza")
        with patch("galerazo_bot.chat_config.t", side_effect=lambda _language, key: key):
            self.assertEqual(chat_config.command_group_label("triggers", "xx"), "Triggers")
            self.assertEqual(chat_config.command_group_label("unknown", "xx"), "unknown")
        self.assertTrue(chat_config.is_valid_language("en"))
        self.assertTrue(chat_config.is_valid_language("es_ES"))
        self.assertTrue(chat_config.is_valid_language("pt_BR"))
        self.assertTrue(chat_config.is_valid_language("zh_Hant"))
        self.assertTrue(chat_config.is_valid_language("gn"))
        self.assertTrue(chat_config.is_valid_language("quz"))
        self.assertEqual({language.code for language in chat_config.LANGUAGES}, set(TRANSLATIONS))
        self.assertFalse(chat_config.is_valid_language("xx"))
        self.assertFalse(chat_config.is_valid_command_group("gastos"))
        self.assertFalse(chat_config.is_valid_command_group("unknown"))
        self.assertIsNone(chat_config.parse_config_callback("bad"))
        self.assertIsNone(chat_config.parse_config_callback("other:main"))
        self.assertEqual(chat_config.parse_config_callback("config:set:gastos:1"), ("set", "gastos", "1"))

    def test_pagination_every_button_shape_and_parser(self) -> None:
        self.assertEqual(pagination._page_button_items(1, 1), [1])
        self.assertEqual(pagination._page_button_items(1, 9), [1, 2, 3, 4, "last"])
        self.assertEqual(pagination._page_button_items(8, 9), ["first", 6, 7, 8, 9])
        self.assertEqual(pagination._page_button_items(5, 9), ["first", 4, 5, 6, "last"])
        keyboard = pagination.build_keyboard("m", 5, 9, True)
        self.assertEqual(keyboard.inline_keyboard[0][0].text, "<<")
        self.assertEqual(keyboard.inline_keyboard[0][-1].text, ">>")
        self.assertEqual(keyboard.inline_keyboard[1][0].text, "🔓")
        locked = pagination.build_keyboard("m", 1, 1, False)
        self.assertEqual(locked.inline_keyboard[0][0].text, "🔒")
        self.assertEqual(locked.inline_keyboard[0][1].text, "❌")
        self.assertEqual(pagination.parse_callback_data("paginated:delete:m"), ("delete", "m", None))
        self.assertIsNone(pagination.parse_callback_data("bad"))
        self.assertIsNone(pagination.parse_callback_data("other:page:m:1"))
        page = pagination.render_page("h", ["123", "456"], 99, max_chars=5)
        self.assertEqual(page.page, 2)
        self.assertEqual(pagination.render_page("h", [], -1).page, 1)


class CommandCoreCompleteTests(unittest.IsolatedAsyncioTestCase):
    def test_command_parsing_all_prefixes(self) -> None:
        self.assertEqual(commands.normalize_command(" /HELP@bot x "), "help")
        self.assertEqual(commands.command_args("/help"), "")
        self.assertEqual(commands.command_args("   "), "")
        self.assertFalse(commands.is_command_invocation("/"))
        self.assertFalse(commands.is_command_invocation(""))
        self.assertFalse(commands.is_command_invocation("help"))
        self.assertTrue(commands.is_command_invocation("!unknown"))
        for text, expected in (
            ("!hola", ("hola", "!")),
            ("plain text", ("plain text", None)),
        ):
            self.assertEqual(commands._strip_command_prefix(text), expected)
        self.assertTrue(commands.command_exists("/hola"))
        self.assertIsNotNone(commands.get_command("/hola"))
        self.assertFalse(commands.command_exists("hola"))
        self.assertIsNone(commands.get_command("hola"))
        self.assertGreater(len(commands.iter_commands()), 1)

    async def test_handler_permission_variants_sync_and_async(self) -> None:
        db = MagicMock()
        denied_key = commands.Command("x", "", MagicMock(), UserLevel.DEV, permission_error_key="salir.permission")
        denied_text = commands.Command("x", "", MagicMock(), UserLevel.DEV, permission_error="custom")
        default = commands.Command("x", "", MagicMock(), UserLevel.DEV)
        sync = commands.Command("x", "", lambda _context, _db: "sync")
        async def async_handler(_context, _db):
            return "async"
        asynchronous = commands.Command("x", "", async_handler)
        context = make_context(raw_text="/x")
        for command, expected in ((denied_key, "permiso"), (denied_text, "custom"), (default, "permisos")):
            with patch.dict(commands.COMMANDS, {"x": command}, clear=True):
                self.assertIn(expected, await commands._handle_with_context(context, db))
        with patch.dict(commands.COMMANDS, {"x": sync}, clear=True):
            self.assertEqual(await commands._handle_with_context(context, db), "sync")
        with patch.dict(commands.COMMANDS, {"x": asynchronous}, clear=True):
            self.assertEqual(await commands._handle_with_context(context, db), "async")
        with patch.dict(commands.COMMANDS, {}, clear=True):
            self.assertIsNone(await commands._handle_with_context(context, db))

    def test_wrappers_language_and_command_post_init(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "db.sqlite3")
            db.register_chat("-1", "group", "G")
            db.set_chat_language("-1", "en")
            self.assertEqual(commands._resolve_language(db, None, "group"), "es")
            self.assertEqual(commands._resolve_language(db, "-1", "private"), "es")
            self.assertEqual(commands._resolve_language(db, "-1", "group"), "en")
            self.assertIn("Hola", commands.handle_text("/hola", "1", db))
            self.assertIn("Hola", commands.handle_command("/hola", "1", db))
        command = commands.Command("two words", "", lambda *_: None)
        self.assertEqual(command.command_key, "two")
        explicit = commands.Command("x", "", lambda *_: None, command_key="key")
        self.assertEqual(explicit.command_key, "key")

    def test_help_other_group_nivel_and_all_role_labels(self) -> None:
        custom = commands.Command("custom", "", lambda *_: None)
        with patch("galerazo_bot.commands.iter_commands", return_value=(custom,)):
            response = help_handler.handle(make_context(), MagicMock())
        self.assertIn("Otros", response)
        self.assertIn("/custom", response)
        self.assertIn("common", nivel.handle(make_context(), MagicMock()))
        self.assertEqual([level.label for level in UserLevel], ["common", "admin", "dev"])

    async def test_roulette_remaining_paths(self) -> None:
        db = MagicMock()
        self.assertIn("grupos", await ruletarusa.ruletarusa(make_context(chat_type="private"), db))
        self.assertIn("configurado", await ruletarusa.ruletarusa(make_context(), db))
        db.play_russian_roulette.return_value = RussianRouletteShot(False, 1)
        configured = replace(
            make_context(),
            can_run_russian_roulette=unittest.mock.AsyncMock(return_value=True),
            resolve_russian_roulette_hit=unittest.mock.AsyncMock(),
        )
        self.assertIn("próximo", await ruletarusa.ruletarusa(configured, db))
        db.play_russian_roulette.return_value = RussianRouletteShot(True, 0)
        for result in RussianRouletteHitResult:
            context = replace(configured, resolve_russian_roulette_hit=unittest.mock.AsyncMock(return_value=result))
            self.assertTrue(await ruletarusa.ruletarusa(context, db))


class ExpenseAndDisplayCompleteTests(unittest.TestCase):
    def test_expense_parsing_formatting_and_labels(self) -> None:
        for raw, expected in (
            ("", None),
            ("ARS | cash | box | desc", None),
            ("0 | cash | box | desc", None),
            ("$ 1.234,56", 123456),
            ("1,234.56", 123456),
            ("12,5", 1250),
            ("1.25", 125),
            ("bad", None),
        ):
            self.assertEqual(expenses.parse_amount_to_cents(raw), expected)
        self.assertIsNone(expenses.parse_expense_command_args("1 | | x | y"))
        self.assertIsNone(expenses.parse_expense_command_args("bad | cash | x | y"))
        self.assertIsNotNone(expenses.parse_expense_command_args("1 | cash | x | y"))
        self.assertEqual(expenses.format_amount(-123456), "ARS -1.234,56")
        self.assertIn("#1", expenses.build_expense_line(1, 1, "USD", "m", "s", "d", "u", "ok"))
        self.assertIn("sincronizado", expenses.sync_status_label("es", True))
        self.assertIn("pendiente", expenses.sync_status_label("es", False))
        self.assertIn("configurado", expenses.fallback_sheet_detail("es", False, False))
        self.assertIn("faltan", expenses.fallback_sheet_detail("es", True, False))
        self.assertIn("listo", expenses.fallback_sheet_detail("es", True, True))
        self.assertIn("/gasto", expenses.expense_usage_example())

    def test_user_resolution_and_format_fallbacks(self) -> None:
        db = MagicMock()
        db.get_or_create_user.return_value = User("2", "Reply", "r")
        reply = make_context(reply_to_user_id="2", reply_to_display_name="Reply", reply_to_username="r")
        self.assertEqual(user_display.resolve_target_user(reply, db).user_id, "2")
        db.get_or_create_user.assert_called_with("2", "Reply", "r")
        self.assertIsNone(user_display.resolve_target_user(make_context(args=""), db))
        user_display.resolve_target_user(make_context(args="22 extra"), db)
        db.get_or_create_user.assert_called_with("22")
        user_display.resolve_target_user(make_context(args="@alias extra"), db)
        db.get_user_by_username.assert_called_with("@alias")
        self.assertEqual(user_display.format_user(User("1", None, "alias"), make_context()), "alias (1)")
        self.assertIn("Usuario", user_display.format_user(User("1", None, None), make_context()))


class ConfigurationAndEntrypointTests(unittest.TestCase):
    def test_settings_all_values_and_helpers(self) -> None:
        environment = {
            "TELEGRAM_BOT_TOKEN": "token",
            "TELEGRAM_DEV_USER_IDS": " 1, ,2 ",
            "TELEGRAM_LOG_CHAT_ID": "-1",
            "TELEGRAM_ANNOUNCEMENTS_CHAT_ID": "-2",
            "TELEGRAM_HISOPO_COMMON_FILE_ID": "common",
            "TELEGRAM_HISOPO_SILVER_FILE_ID": "silver",
            "TELEGRAM_HISOPO_GOLD_FILE_ID": "gold",
            "TELEGRAM_HISOPO_DIAMOND_FILE_ID": "diamond",
            "TELEGRAM_HISOPO_FLEETING_FILE_ID": "fleeting",
            "TELEGRAM_HISOPO_MYSTERY_FILE_ID": "mystery",
            "TELEGRAM_HISOPO_PUTRID_FILE_ID": "putrid",
            "TELEGRAM_HISOPO_RADIOACTIVE_FILE_ID": "radioactive",
            "TELEGRAM_HISOPO_BOMB_FILE_ID": "bomb",
            "TELEGRAM_HISOPO_BOMB_DEFUSED_FILE_ID": "bomb-defused",
            "TELEGRAM_HISOPO_BOMB_EXPLODED_FILE_ID": "bomb-exploded",
            "TELEGRAM_HISOPO_FRENETIC_FILE_ID": "frenetic",
            "TELEGRAM_HISOPO_BLACK_HOLE_FILE_ID": "black-hole",
            "TELEGRAM_HISOPO_EXPIRED_FILE_ID": "expired",
            "TELEGRAM_HISOPO_FAKE_FILE_ID": "fake",
            "TELEGRAM_HISOPO_TWIN_FILE_ID": "twin",
            "TELEGRAM_HISOPO_GIANT_FILE_ID": "giant",
            "TELEGRAM_HISOPO_MIRACLE_FILE_ID": "miracle",
            "DATABASE_PATH": "db.sqlite3",
            "GOOGLE_SHEETS_CREDENTIALS_JSON_PATH": "key.json",
            "GOOGLE_SHEETS_SPREADSHEET_ID": "sheet",
            "GOOGLE_SHEETS_WORKSHEET_NAME": "Tab",
            "OPENAI_API_KEY": "openai",
            "GOOGLE_CLOUD_BILLING_PROJECT_ID": "project",
            "GOOGLE_CLOUD_BILLING_TABLE": "project1.dataset.table",
            "GOOGLE_CLOUD_BILLING_REPORT_TIME": "10:30",
        }
        with patch.dict("os.environ", environment, clear=True):
            settings = config.load_settings()
        self.assertEqual(settings.telegram_dev_user_ids, frozenset({"1", "2"}))
        self.assertEqual(settings.google_sheets_credentials_json_path, Path("key.json"))
        self.assertEqual(settings.telegram_hisopo_common_file_id, "common")
        self.assertEqual(settings.telegram_hisopo_silver_file_id, "silver")
        self.assertEqual(settings.telegram_hisopo_gold_file_id, "gold")
        self.assertEqual(settings.telegram_hisopo_diamond_file_id, "diamond")
        self.assertEqual(settings.telegram_hisopo_fleeting_file_id, "fleeting")
        self.assertEqual(settings.telegram_hisopo_mystery_file_id, "mystery")
        self.assertEqual(settings.telegram_hisopo_putrid_file_id, "putrid")
        self.assertEqual(settings.telegram_hisopo_radioactive_file_id, "radioactive")
        self.assertEqual(settings.telegram_hisopo_bomb_file_id, "bomb")
        self.assertEqual(settings.telegram_hisopo_bomb_defused_file_id, "bomb-defused")
        self.assertEqual(settings.telegram_hisopo_bomb_exploded_file_id, "bomb-exploded")
        self.assertEqual(settings.telegram_hisopo_frenetic_file_id, "frenetic")
        self.assertEqual(settings.telegram_hisopo_black_hole_file_id, "black-hole")
        self.assertEqual(settings.telegram_hisopo_expired_file_id, "expired")
        self.assertEqual(settings.telegram_hisopo_fake_file_id, "fake")
        self.assertEqual(settings.telegram_hisopo_twin_file_id, "twin")
        self.assertEqual(settings.telegram_hisopo_giant_file_id, "giant")
        self.assertEqual(settings.telegram_hisopo_miracle_file_id, "miracle")
        self.assertIsNone(config._optional_path(None))
        self.assertEqual(config._optional_path("x"), Path("x"))

    def test_cli_and_deploy_backup_entrypoints(self) -> None:
        settings = SimpleNamespace(database_path=Path("unused"))
        with (
            patch("sys.argv", ["cli", "hola", "mundo"]),
            patch("galerazo_bot.cli.load_settings", return_value=settings),
            patch("galerazo_bot.cli.Database", return_value=MagicMock()),
            patch("galerazo_bot.cli.handle_text", return_value="response") as handle,
            redirect_stdout(io.StringIO()) as output,
        ):
            cli.main()
        self.assertEqual(output.getvalue().strip(), "response")
        handle.assert_called_once()
        with (
            patch("galerazo_bot.deploy_backup.create_deploy_backup", return_value=Path("backup.sqlite3")),
            redirect_stdout(io.StringIO()) as output,
        ):
            self.assertEqual(deploy_backup.main(), 0)
        self.assertIn("backup.sqlite3", output.getvalue())
        with patch("galerazo_bot.deploy_backup.load_settings", return_value=settings), patch.dict(
            "os.environ", {"BACKUPS_PATH": "copies"}
        ), patch("galerazo_bot.deploy_backup.Database") as database:
            database.return_value.create_backup.return_value = Path("copies/db")
            self.assertEqual(deploy_backup.create_deploy_backup(), Path("copies/db"))

    def test_module_entrypoint_guards(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database_path = root / "db.sqlite3"
            Database(database_path)
            environment = {
                "DATABASE_PATH": str(database_path),
                "BACKUPS_PATH": str(root / "backups"),
            }
            with patch.dict("os.environ", environment, clear=True), patch(
                "sys.argv", ["cli", "hola"]
            ), redirect_stdout(io.StringIO()):
                runpy.run_module("galerazo_bot.cli", run_name="__main__")
            with patch.dict("os.environ", environment, clear=True), redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as deploy_exit:
                    runpy.run_module("galerazo_bot.deploy_backup", run_name="__main__")
                self.assertEqual(deploy_exit.exception.code, 0)
                with self.assertRaises(SystemExit) as health_exit:
                    runpy.run_module("galerazo_bot.healthcheck", run_name="__main__")
                self.assertEqual(health_exit.exception.code, 0)

    def test_runtime_success_and_failure(self) -> None:
        with patch.object(runtime, "PYTHON_VERSION_FILE", Path(".python-version")):
            self.assertRegex(runtime.required_python_version(), r"^\d+\.\d+\.\d+$")
        with patch.object(runtime, "required_python_version", return_value="1.2.3"), patch(
            "galerazo_bot.runtime.platform.python_version", return_value="1.2.4"
        ):
            with self.assertRaisesRegex(RuntimeError, "py -1.2"):
                runtime.ensure_python_version()


class BillingSheetsHealthAndStatusTests(unittest.IsolatedAsyncioTestCase):
    def test_billing_remaining_format_and_conversion_paths(self) -> None:
        self.assertFalse(cloud_billing.GoogleCloudBillingConfig(None, None).is_configured)
        self.assertEqual(cloud_billing._as_decimal(None), Decimal("0"))
        value = Decimal("1.2")
        self.assertIs(cloud_billing._as_decimal(value), value)
        self.assertEqual(cloud_billing._as_decimal(2), Decimal("2"))
        first = datetime(2026, 1, 1)
        second = datetime(2026, 1, 2, tzinfo=timezone.utc)
        rows = [
            SimpleNamespace(currency="USD", gross_cost=None, credits=Decimal("-1"), net_cost="2", latest_export_time=None),
            SimpleNamespace(currency="ARS", gross_cost=1, credits=0, net_cost=1, latest_export_time=second),
        ]
        report = cloud_billing._build_report("202601", rows)
        self.assertEqual(report.latest_export_time, second)
        naive_report = replace(report, latest_export_time=first)
        self.assertIn("Argentina", cloud_billing.format_google_cloud_billing_report(naive_report))
        self.assertNotIn(
            "Datos actualizados",
            cloud_billing.format_google_cloud_billing_report(replace(report, latest_export_time=None)),
        )
        self.assertEqual(cloud_billing._format_decimal(Decimal("1234.5")), "1.234,50")
        with patch("galerazo_bot.cloud_billing.bigquery.Client") as client:
            cloud_billing._create_bigquery_client("project")
        client.assert_called_once_with(project="project")

    async def test_billing_reader_missing_runtime_config(self) -> None:
        reader = cloud_billing.GoogleCloudBillingReader(cloud_billing.GoogleCloudBillingConfig(None, None))
        with self.assertRaises(RuntimeError):
            await reader.get_month_to_date()
        with self.assertRaises(RuntimeError):
            reader._query("202601")

    def test_google_sheets_all_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            key = Path(directory) / "key.json"
            configured = google_sheets.GoogleSheetsExpenseWriter(
                google_sheets.GoogleSheetsConfig(key, "sheet", "Tab")
            )
            missing = google_sheets.GoogleSheetsExpenseWriter(
                google_sheets.GoogleSheetsConfig(None, None, "Tab")
            )
            self.assertEqual(configured.worksheet_name, "Tab")
            self.assertFalse(missing.is_configured())
            self.assertFalse(missing.is_ready())
            self.assertEqual(missing.append_expense_row([]), (False, "sheet_not_configured"))
            self.assertEqual(configured.append_expense_row([]), (False, "sheet_not_ready"))
            key.write_text("{}", encoding="utf-8")
            worksheet = MagicMock()
            worksheet.get.return_value = []
            spreadsheet = MagicMock()
            spreadsheet.worksheet.return_value = worksheet
            client = MagicMock()
            client.open_by_key.return_value = spreadsheet
            fake_gspread = MagicMock()
            fake_gspread.service_account.return_value = client
            with patch.object(google_sheets, "gspread", fake_gspread):
                self.assertTrue(configured.is_ready())
                self.assertEqual(configured.append_expense_row(["x"]), (True, None))
            worksheet.append_row.assert_any_call(list(google_sheets.EXPENSE_HEADERS), value_input_option="RAW")
            worksheet.append_row.assert_any_call(["x"], value_input_option="USER_ENTERED")
            worksheet.get.return_value = [["header"]]
            configured._ensure_headers(worksheet)
            spreadsheet.worksheet.side_effect = RuntimeError
            spreadsheet.add_worksheet.return_value = worksheet
            self.assertIs(configured._get_or_create_worksheet(spreadsheet), worksheet)
            fake_gspread.service_account.side_effect = RuntimeError("api")
            with patch.object(google_sheets, "gspread", fake_gspread):
                self.assertEqual(configured.append_expense_row([]), (False, "api"))
            with patch.object(google_sheets, "gspread", None):
                self.assertFalse(configured.is_ready())

    def test_healthcheck_success_missing_and_bad_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "db.sqlite3"
            sqlite3.connect(db).close()
            settings = SimpleNamespace(database_path=db)
            with patch("galerazo_bot.healthcheck.load_settings", return_value=settings):
                healthcheck.check_database()
            with patch("galerazo_bot.healthcheck.load_settings", return_value=SimpleNamespace(database_path=Path("missing"))):
                with self.assertRaisesRegex(RuntimeError, "does not exist"):
                    healthcheck.check_database()
            connection = MagicMock()
            connection.execute.return_value.fetchone.return_value = (2,)
            with patch("galerazo_bot.healthcheck.load_settings", return_value=settings), patch(
                "galerazo_bot.healthcheck.sqlite3.connect", return_value=connection
            ):
                with self.assertRaisesRegex(RuntimeError, "unexpected"):
                    healthcheck.check_database()
        with patch("galerazo_bot.healthcheck.check_database"):
            self.assertEqual(healthcheck.main(), 0)
        with patch("galerazo_bot.healthcheck.check_database", side_effect=RuntimeError("bad")):
            self.assertEqual(healthcheck.main(), 1)

    def test_integration_status_invalid_shapes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "status.json"
            with patch.object(integration_status, "STATUS_PATH", path):
                self.assertIsNone(integration_status.load_logging_status())
                path.write_text("bad", encoding="utf-8")
                self.assertIsNone(integration_status.load_logging_status())
                path.write_text(json.dumps({"logging": "bad"}), encoding="utf-8")
                self.assertIsNone(integration_status.load_logging_status())
                integration_status.save_logging_status(True, "ok")
                self.assertTrue(integration_status.load_logging_status()["ok"])

    def test_logging_redaction_filter_and_idempotence(self) -> None:
        import logging

        record = logging.LogRecord("x", logging.INFO, "", 1, "token 123456:abcdefgh", (), None)
        self.assertTrue(logging_utils.SecretRedactionFilter().filter(record))
        self.assertIn("<redacted>", record.msg)
        handler = logging.StreamHandler(io.StringIO())
        root = logging.getLogger()
        with patch.object(root, "handlers", [handler]):
            logging_utils.configure_logging()
            logging_utils.configure_logging()
        self.assertEqual(sum(isinstance(f, logging_utils.SecretRedactionFilter) for f in handler.filters), 1)
        self.assertEqual(sum(isinstance(f, logging_utils.SuccessfulGetUpdatesFilter) for f in handler.filters), 1)
        self.assertIsInstance(handler.formatter, logging_utils.ExceptionFirstFormatter)
        self.assertEqual(root.level, logging.DEBUG)


if __name__ == "__main__":
    unittest.main()
