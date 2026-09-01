from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import (
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    Chat,
    ChatMember,
    Message,
    Update,
    User,
)
from telegram.error import BadRequest, Conflict, Forbidden, NetworkError, TelegramError, TimedOut

from galerazo_bot.cloud_billing import GoogleCloudBillingReader, GoogleCloudBillingReport
from galerazo_bot.config import Settings
from galerazo_bot.database import (
    Database,
    Expense,
    HisopoCaptureResult,
    HisopoBombResult,
    HisopoExpirationResult,
    HisopoGiantContributionResult,
    HisopoMessageCleanup,
    HisopoSchedule,
    HisopoSpawn,
    HisopoRaceResult,
    PaginatedMessageState,
    RestartConfirmation,
    Trigger,
)
from galerazo_bot.google_sheets import GoogleSheetsConfig, GoogleSheetsExpenseWriter
from galerazo_bot.google_sheets import ExpenseSheetWriteResult
from galerazo_bot.exchange_rates import ExchangeRateError, ExchangeRateQuote
from galerazo_bot.expenses import ExpenseDraft, ExpenseMovement
from galerazo_bot.roles import TriggerModerationResult, TriggerPayload, UserLevel
from galerazo_bot import telegram_bot as tb
from galerazo_bot.command_handlers import galerazas as galeraza_handlers


def settings(**overrides) -> Settings:
    values = dict(
        telegram_bot_token="token",
        telegram_dev_user_ids=frozenset({"1"}),
        telegram_owner_user_id="1",
        telegram_log_chat_id="-10",
        telegram_announcements_chat_id="-11",
        database_path=Path("db.sqlite3"),
        google_sheets_credentials_json_path=None,
        google_sheets_spreadsheet_id=None,
        google_sheets_worksheet_name="Gastos",
        openai_api_key=None,
        google_cloud_billing_project_id=None,
        google_cloud_billing_table=None,
        google_cloud_billing_report_time="09:00",
    )
    values.update(overrides)
    return Settings(**values)


def state(db=None, **setting_overrides) -> tb.BotState:
    return tb.BotState(
        db=db or MagicMock(),
        settings=settings(**setting_overrides),
        bot_user_id="99",
        expense_sheet_writer=MagicMock(spec=GoogleSheetsExpenseWriter),
        media_moderator=SimpleNamespace(enabled=False),
    )


def context_for(bot_state: tb.BotState, bot=None):
    return SimpleNamespace(
        application=SimpleNamespace(bot_data={"state": bot_state}),
        bot=bot or MagicMock(),
    )


def message_stub(**overrides):
    values = dict(
        chat=SimpleNamespace(id=-1, type="group", title="Group"),
        message_id=10,
        text=None,
        caption=None,
        reply_to_message=None,
        from_user=None,
        new_chat_members=None,
        left_chat_member=None,
        migrate_to_chat_id=None,
        migrate_from_chat_id=None,
        photo=None,
        video=None,
        animation=None,
        audio=None,
        voice=None,
        document=None,
        video_note=None,
        sticker=None,
        dice=None,
        contact=None,
        venue=None,
        location=None,
        poll=None,
        date=datetime(2026, 7, 22, 3, tzinfo=timezone.utc),
        reply_text=AsyncMock(),
        reply_document=AsyncMock(),
        edit_text=AsyncMock(),
        delete=AsyncMock(),
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def trigger(media_type=None, file_id=None, text=None, payload_json=None, caption="cap") -> Trigger:
    return Trigger("-1", "name", "Name", text, media_type, file_id, caption, "1", "now", payload_json)


class LifecycleAndBillingTests(unittest.IsolatedAsyncioTestCase):
    def test_panel_managed_restart_refreshes_the_pid_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pid_path = Path(directory) / "bot.pid"
            restart_path = Path(directory) / "bot.restart"
            with patch.object(tb, "PANEL_PID_PATH", pid_path), patch.object(
                tb, "PANEL_RESTART_PATH", restart_path
            ), patch.dict(
                tb.os.environ, {}, clear=True
            ):
                tb._record_panel_managed_pid()
                tb._mark_panel_restart_pending()
                self.assertFalse(pid_path.exists())
                self.assertFalse(restart_path.exists())

            with patch.object(tb, "PANEL_PID_PATH", pid_path), patch.object(
                tb, "PANEL_RESTART_PATH", restart_path
            ), patch.dict(
                tb.os.environ, {tb.PANEL_MANAGED_ENV: "1"}, clear=True
            ):
                tb._mark_panel_restart_pending()
                self.assertTrue(restart_path.exists())
                tb._record_panel_managed_pid()
            self.assertEqual(pid_path.read_text(encoding="ascii"), str(tb.os.getpid()))
            self.assertFalse(restart_path.exists())

    def test_bold_empty_main_failures_success_and_handler_registration(self) -> None:
        self.assertEqual(tb._bold_first_line_entities(""), [])
        with patch.object(tb, "ensure_python_version"), patch.object(tb, "configure_logging"), patch.object(
            tb, "load_settings", return_value=settings(telegram_bot_token="")
        ):
            with self.assertRaisesRegex(RuntimeError, "TELEGRAM_BOT_TOKEN"):
                tb.main()

        lock = MagicMock()
        lock.acquire.return_value = False
        with patch.object(tb, "ensure_python_version"), patch.object(tb, "configure_logging"), patch.object(
            tb, "load_settings", return_value=settings()
        ), patch.object(tb, "SingleInstance", return_value=lock):
            with self.assertRaisesRegex(RuntimeError, "otra instancia"):
                tb.main()

        lock.acquire.return_value = True
        application = MagicMock()
        fake_db = MagicMock()
        with patch.object(tb, "ensure_python_version"), patch.object(tb, "configure_logging"), patch.object(
            tb, "load_settings", return_value=settings()
        ), patch.object(tb, "SingleInstance", return_value=lock), patch.object(
            tb, "Database", return_value=fake_db
        ), patch.object(tb, "_build_application", return_value=application), patch.object(
            tb, "_register_handlers"
        ):
            tb.main()
        application.run_polling.assert_called_once_with(**tb.POLLING_OPTIONS)
        lock.release.assert_called_once()

        restart_application = MagicMock()
        restart_application.bot_data = {"restart_requested": True}
        with patch.object(tb, "ensure_python_version"), patch.object(tb, "configure_logging"), patch.object(
            tb, "load_settings", return_value=settings()
        ), patch.object(tb, "SingleInstance", return_value=lock), patch.object(
            tb, "Database", return_value=fake_db
        ), patch.object(tb, "_build_application", return_value=restart_application), patch.object(
            tb, "_register_handlers"
        ), patch.object(tb.os, "execv") as restart:
            tb.main()
        restart.assert_called_once_with(tb.sys.executable, [tb.sys.executable, *tb.sys.argv])

        fake_application = MagicMock()
        with patch.dict(tb.COMMANDS, {"hola": MagicMock(), "help": MagicMock()}, clear=True):
            tb._register_handlers(fake_application)
        self.assertEqual(fake_application.add_handler.call_count, 13)

    def test_build_application_uses_per_chat_processor(self) -> None:
        db = MagicMock()
        builder = MagicMock()
        builder.bot.return_value = builder
        builder.post_init.return_value = builder
        builder.post_shutdown.return_value = builder
        builder.concurrent_updates.return_value = builder
        builder.build.return_value = "app"
        retrying_bot = MagicMock()
        with patch.object(tb, "ApplicationBuilder", return_value=builder), patch.object(
            tb, "build_retrying_ext_bot", return_value=retrying_bot
        ) as build_bot:
            self.assertEqual(tb._build_application("token", db), "app")
        build_bot.assert_called_once_with("token", tb.TELEGRAM_REQUEST_TIMEOUT_SECONDS)
        builder.bot.assert_called_once_with(retrying_bot)
        builder.post_shutdown.assert_called_once_with(tb._post_shutdown)
        self.assertIsInstance(builder.concurrent_updates.call_args.args[0], tb.PerChatUpdateProcessor)

    async def test_botfather_command_suggestions_are_public_and_scoped(self) -> None:
        private_names = {
            command.command for command in tb._suggested_bot_commands("es", UserLevel.COMMON, False)
        }
        group_names = {
            command.command for command in tb._suggested_bot_commands("es", UserLevel.COMMON, True)
        }
        admin_names = {
            command.command for command in tb._suggested_bot_commands("es", UserLevel.ADMIN, True)
        }
        english_commands = tb._suggested_bot_commands("en", UserLevel.ADMIN, True)
        hidden_expenses = {
            "gasto",
            "pagoresumen",
            "cierre",
            "ayudagastos",
            "ultimosgastos",
            "estadogastos",
            "sincronizargastos",
        }
        for level in UserLevel:
            self.assertTrue(
                hidden_expenses.isdisjoint(
                    command.command
                    for command in tb._suggested_bot_commands("es", level, True)
                )
            )

        self.assertEqual(
            private_names,
            {
                "help", "ayuda", "start", "hola", "lil", "nivel", "version",
                "chats", "reportar", "donar", "donantes", "paysupport", "terminos",
                "config", "debug", "reglashisopo",
            },
        )
        self.assertTrue(
            {
                "galeraza",
                "galerazas",
                "triggers",
                "agregartrigger",
                "coleccionhisopos",
                "reglashisopo",
            }
            <= group_names
        )
        self.assertIn("ruletarusa", group_names)
        self.assertIn("debug", group_names)
        self.assertFalse({"config", "backup", "gasto"} & group_names)
        self.assertTrue({"config", "restringir", "habilitar", "restringidos", "reglashisopo"} <= admin_names)
        self.assertIn("debug", admin_names)
        self.assertFalse({"backup", "gasto", "estadogastos"} & admin_names)
        self.assertIn("shows this help", {command.description for command in english_commands})
        self.assertIn(
            "shows the Swab Collector rules",
            {command.description for command in english_commands},
        )
        self.assertIn(
            "shows your historical Swab collection",
            {command.description for command in english_commands},
        )

        bot = SimpleNamespace(set_my_commands=AsyncMock(), delete_my_commands=AsyncMock())
        await tb._sync_botfather_commands(bot)
        self.assertEqual(bot.set_my_commands.await_count, 6)
        self.assertEqual(bot.delete_my_commands.await_count, 2)
        scopes = [call.kwargs["scope"] for call in bot.set_my_commands.await_args_list]
        self.assertEqual(sum(isinstance(scope, BotCommandScopeAllPrivateChats) for scope in scopes), 2)
        self.assertEqual(sum(isinstance(scope, BotCommandScopeAllGroupChats) for scope in scopes), 2)
        self.assertEqual(sum(isinstance(scope, BotCommandScopeAllChatAdministrators) for scope in scopes), 2)

        bot.set_my_commands.side_effect = TimedOut()
        await tb._sync_botfather_commands(bot)

    async def test_post_init_builds_state_and_runs_startup_actions(self) -> None:
        db = MagicMock()
        app = SimpleNamespace(
            bot_data={"settings": settings(), "db": db},
            bot=SimpleNamespace(
                get_me=AsyncMock(return_value=SimpleNamespace(id=99, username="galerazo_bot"))
            ),
        )
        with patch.object(tb, "_sync_botfather_commands", AsyncMock()) as sync, patch.object(
            tb, "_announce_current_release", AsyncMock()
        ) as announce, patch.object(
            tb, "_cleanup_old_paginated_messages", AsyncMock()
        ) as cleanup, patch.object(
            tb, "_send_log_event", AsyncMock(return_value=True)
        ) as log, patch.object(
            tb, "_configure_mini_app", AsyncMock(return_value=False)
        ) as configure_mini_app, patch.object(tb, "_schedule_google_cloud_billing_report") as schedule:
            await tb._post_init(app)
        self.assertEqual(app.bot_data["state"].bot_user_id, "99")
        self.assertEqual(app.bot_data["state"].bot_username, "galerazo_bot")
        sync.assert_awaited_once_with(app.bot)
        configure_mini_app.assert_awaited_once_with(app)
        announce.assert_awaited_once_with(db, app.bot, app.bot_data["settings"])
        cleanup.assert_awaited_once()
        log.assert_awaited_once()
        schedule.assert_called_once()

    async def test_release_announcement_only_marks_version_after_success(self) -> None:
        db = MagicMock()
        bot = MagicMock()
        db.get_announced_release_version.return_value = tb.CURRENT_VERSION
        self.assertFalse(await tb._announce_current_release(db, bot, settings()))

        db.get_announced_release_version.return_value = None
        with patch.object(tb, "release_broadcast_notes", side_effect=ValueError("bad")), patch.object(
            tb, "_send_log_event", AsyncMock(return_value=True)
        ) as log:
            self.assertFalse(await tb._announce_current_release(db, bot, settings()))
        log.assert_awaited_once_with(
            bot,
            "-10",
            f"No pude preparar el broadcast de novedades de la version {tb.CURRENT_VERSION}: "
            "bad. La version queda pendiente.",
        )

        with patch.object(tb, "release_broadcast_notes", return_value="notes"), patch.object(
            tb, "_broadcast_announcement", AsyncMock(return_value=tb.AnnouncementBroadcastResult())
        ), patch.object(tb, "_send_log_event", AsyncMock(return_value=True)) as log:
            self.assertFalse(await tb._announce_current_release(db, bot, settings()))
        log.assert_awaited_once_with(
            bot,
            "-10",
            f"No pude completar el anuncio de novedades de la version {tb.CURRENT_VERSION}: "
            "el canal de anuncios no confirmo el envio. La version queda pendiente.",
        )

        with patch.object(tb, "release_broadcast_notes", return_value="notes"), patch.object(
            tb,
            "_broadcast_announcement",
            AsyncMock(return_value=tb.AnnouncementBroadcastResult(too_long=True)),
        ), patch.object(tb, "maximum_formatted_announcement_length", return_value=5000), patch.object(
            tb, "_send_log_event", AsyncMock(return_value=True)
        ) as log:
            self.assertFalse(await tb._announce_current_release(db, bot, settings()))
        log.assert_awaited_once_with(
            bot,
            "-10",
            f"No pude anunciar las novedades de la version {tb.CURRENT_VERSION}: "
            "el mensaje final tiene 5000 caracteres y supera el limite de Telegram de 4096. "
            "La version queda pendiente.",
        )

        with patch.object(tb, "release_broadcast_notes", return_value="notes"), patch.object(
            tb,
            "_broadcast_announcement",
            AsyncMock(return_value=tb.AnnouncementBroadcastResult(announcement_channel_sent=True)),
        ) as send, patch.object(tb, "_send_log_event", AsyncMock(return_value=True)) as log:
            self.assertTrue(await tb._announce_current_release(db, bot, settings()))
        send.assert_awaited_once_with(db=db, bot=bot, text="notes", announcements_chat_id="-11")
        log.assert_awaited_once_with(
            bot,
            "-10",
            "Anuncio terminado.\nEnviados: 0.\nOmitidos: 0.\nInactivos detectados: 0.\nFallidos transitorios: 0.\nCanal de anuncios: si.",
        )
        db.set_announced_release_version.assert_called_once_with(tb.CURRENT_VERSION)

    def test_schedule_invalid_reader_time_and_missing_job_queue(self) -> None:
        app = SimpleNamespace(job_queue=MagicMock())
        self.assertFalse(tb._schedule_google_cloud_billing_report(app, settings(telegram_log_chat_id=None)))
        self.assertFalse(tb._schedule_google_cloud_billing_report(app, settings()))
        configured = settings(
            google_cloud_billing_project_id="project1",
            google_cloud_billing_table="invalid",
        )
        self.assertFalse(tb._schedule_google_cloud_billing_report(app, configured))
        configured = replace(
            configured,
            google_cloud_billing_table="project1.dataset.table",
            google_cloud_billing_report_time="bad",
        )
        self.assertFalse(tb._schedule_google_cloud_billing_report(app, configured))
        with self.assertRaisesRegex(RuntimeError, "job-queue"):
            tb._schedule_google_cloud_billing_report(SimpleNamespace(job_queue=None), replace(configured, google_cloud_billing_report_time="09:00"))

    async def test_billing_job_invalid_valid_and_report_failure(self) -> None:
        app = SimpleNamespace(bot_data={"settings": settings()})
        invalid = SimpleNamespace(job=None, application=app, bot=MagicMock())
        await tb._google_cloud_billing_report_job(invalid)
        reader = MagicMock(spec=GoogleCloudBillingReader)
        valid = SimpleNamespace(job=SimpleNamespace(data=reader), application=app, bot=MagicMock())
        with patch.object(tb, "_send_google_cloud_billing_report", AsyncMock(return_value=True)) as send:
            await tb._google_cloud_billing_report_job(valid)
        send.assert_awaited_once_with(valid.bot, "-10", reader)

        reader.get_month_to_date = AsyncMock(return_value=GoogleCloudBillingReport("202607", (), None))
        with patch.object(tb, "_send_log_event", AsyncMock(return_value=True)) as log:
            self.assertTrue(await tb._send_google_cloud_billing_report(valid.bot, "-10", reader))
        self.assertIn("gasto mensual", log.await_args.args[2])
        reader.get_month_to_date.side_effect = RuntimeError("billing")
        with patch.object(tb, "_send_log_event", AsyncMock(return_value=False)) as log:
            self.assertFalse(await tb._send_google_cloud_billing_report(valid.bot, "-10", reader))
        self.assertIn("No pude consultar", log.await_args.args[2])


class PreprocessAndTriggerTests(unittest.IsolatedAsyncioTestCase):
    async def test_preprocess_early_paths_and_full_text_path(self) -> None:
        db = MagicMock()
        bot_state = state(db)
        context = context_for(bot_state, MagicMock())
        await tb._preprocess_message(SimpleNamespace(effective_message=None), context)
        migration = message_stub(migrate_to_chat_id=-100)
        await tb._preprocess_message(SimpleNamespace(effective_message=migration), context)
        db.get_or_create_user.assert_not_called()
        with patch.object(tb, "_handle_chat_migration") as handle_migration:
            await tb._chat_migration_entrypoint(
                SimpleNamespace(effective_message=migration),
                context,
            )
        handle_migration.assert_called_once_with(migration, db)
        await tb._chat_migration_entrypoint(SimpleNamespace(effective_message=None), context)

        message = message_stub(text="hello")
        update = SimpleNamespace(effective_message=message, effective_user=None, effective_chat=message.chat)
        await tb._preprocess_message(update, context)
        user = SimpleNamespace(id=1, full_name="User", username=None, is_bot=False)
        update.effective_user = user
        db.is_user_blocked.return_value = True
        await tb._preprocess_message(update, context)
        db.is_user_blocked.return_value = False
        with patch.object(tb, "_is_user_restricted_in_message_chat", return_value=True):
            await tb._preprocess_message(update, context)

        with patch.object(tb, "_is_user_restricted_in_message_chat", return_value=False), patch.object(
            tb, "_is_galeraza_candidate", return_value=True), patch.object(
            tb, "_maybe_award_daily_galeraza", AsyncMock()
        ) as award, patch.object(
            tb, "_maybe_spawn_hisopo_for_message", AsyncMock()
        ), patch.object(tb, "_maybe_send_triggered_messages", AsyncMock()) as send:
            await tb._preprocess_message(update, context)
        award.assert_awaited_once()
        send.assert_awaited_once()
        db.save_incoming_message.assert_called_with(sender_id="1", text="hello", chat_id="-1")

        message.text = "/hola"
        with patch.object(tb, "_is_user_restricted_in_message_chat", return_value=False), patch.object(
            tb, "_is_galeraza_candidate", return_value=False), patch.object(
            tb, "_maybe_send_triggered_messages", AsyncMock()
        ) as send:
            await tb._preprocess_message(update, context)
        send.assert_not_awaited()

    async def test_preprocess_logs_galeraza_timeout_and_continues(self) -> None:
        db = MagicMock()
        db.is_user_blocked.return_value = False
        context = context_for(state(db), MagicMock())
        message = message_stub(text="primer mensaje")
        user = SimpleNamespace(id=1, full_name="User", username=None, is_bot=False)
        update = SimpleNamespace(
            update_id=42,
            effective_message=message,
            effective_user=user,
            effective_chat=message.chat,
        )

        with patch.object(tb, "_is_user_restricted_in_message_chat", return_value=False), patch.object(
            tb, "_is_galeraza_candidate", return_value=True
        ), patch.object(
            tb, "_maybe_award_daily_galeraza", AsyncMock(side_effect=TimedOut())
        ), patch.object(
            tb, "_send_log_event", AsyncMock(return_value=True)
        ) as log, patch.object(
            tb, "_maybe_spawn_hisopo_for_message", AsyncMock()
        ), patch.object(
            tb, "_maybe_send_triggered_messages", AsyncMock()
        ) as send, self.assertLogs(tb.logger, level="ERROR") as captured:
            await tb._preprocess_message(update, context)

        timeout_log = log.await_args.args[2]
        self.assertTrue(timeout_log.startswith("TimedOut: Timed out\n"))
        self.assertIn("TimedOut", timeout_log)
        self.assertIn("El punto se conservo", timeout_log)
        self.assertIn("pudieron haberse enviado igualmente", timeout_log)
        self.assertIn("3 intentos totales", timeout_log)
        self.assertIn("pueden estar duplicados", timeout_log)
        self.assertIn("update_id=42 chat_id=-1 message_id=10", timeout_log)
        self.assertIn("telegram.error.TimedOut", "\n".join(captured.output))
        send.assert_awaited_once()
        db.save_incoming_message.assert_called_with(sender_id="1", text="primer mensaje", chat_id="-1")

    async def test_maybe_triggered_early_match_nonmatch_and_error(self) -> None:
        db = MagicMock()
        bot = MagicMock()
        private = message_stub(chat=SimpleNamespace(id=1, type="private"))
        await tb._maybe_send_triggered_messages(db, bot, private)
        message = message_stub(text="contains name")
        db.is_command_group_enabled.return_value = False
        await tb._maybe_send_triggered_messages(db, bot, message)
        db.is_command_group_enabled.return_value = True
        message.text = None
        await tb._maybe_send_triggered_messages(db, bot, message)
        message.text = "contains name"
        db.list_triggers.return_value = [trigger(text="x"), replace(trigger(text="x"), trigger_name="absent")]
        with patch.object(tb, "_send_trigger_message", AsyncMock(side_effect=TelegramError("send"))) as send:
            await tb._maybe_send_triggered_messages(db, bot, message)
        send.assert_awaited_once()

    async def test_send_every_trigger_media_type_and_payload_parser(self) -> None:
        bot = SimpleNamespace(**{name: AsyncMock() for name in (
            "send_photo", "send_video", "send_animation", "send_audio", "send_voice",
            "send_document", "send_video_note", "send_sticker", "send_dice", "send_contact",
            "send_location", "send_venue", "send_poll", "send_message"
        )})
        cases = (
            ("photo", "send_photo", "photo"),
            ("video", "send_video", "video"),
            ("animation", "send_animation", "animation"),
            ("audio", "send_audio", "audio"),
            ("voice", "send_voice", "voice"),
            ("document", "send_document", "document"),
            ("video_note", "send_video_note", "video_note"),
            ("sticker", "send_sticker", "sticker"),
        )
        for media_type, method, _field in cases:
            await tb._send_trigger_message(bot, -1, trigger(media_type, "file"))
            self.assertEqual(getattr(bot, method).await_count, 1)
        await tb._send_trigger_message(bot, -1, trigger("dice", text="🎲"))
        for media_type, method in (("contact", "send_contact"), ("location", "send_location"), ("venue", "send_venue"), ("poll", "send_poll")):
            await tb._send_trigger_message(bot, -1, trigger(media_type, payload_json='{"x": 1}'))
            self.assertEqual(getattr(bot, method).await_count, 1)
        await tb._send_trigger_message(bot, -1, trigger(text="x" * 5000))
        self.assertEqual(len(bot.send_message.await_args.kwargs["text"]), 4096)
        await tb._send_trigger_message(bot, -1, trigger("unknown", payload_json="[]"))
        self.assertIsNone(tb._trigger_payload_data(trigger()))
        self.assertIsNone(tb._trigger_payload_data(trigger(payload_json="bad")))
        self.assertIsNone(tb._trigger_payload_data(trigger(payload_json="[]")))
        self.assertEqual(tb._trigger_payload_data(trigger(payload_json='{"x":1}')), {"x": 1})

    async def test_command_entrypoint_forwards_to_the_shared_command_handler(self) -> None:
        context = MagicMock()
        with patch.object(tb, "_handle_command_update", AsyncMock()) as handler:
            await tb._command_entrypoint(SimpleNamespace(), context)
        handler.assert_awaited_once()


class CommandAndCallbackEntrypointTests(unittest.IsolatedAsyncioTestCase):
    async def test_handle_command_guards_blocking_and_disabled_group(self) -> None:
        db = MagicMock()
        bot_state = state(db)
        context = context_for(bot_state, MagicMock())
        chat = SimpleNamespace(id=-1, type="group")
        user = SimpleNamespace(id=1, full_name="User", username=None)
        cases = (
            SimpleNamespace(effective_message=None, effective_user=user, effective_chat=chat),
            SimpleNamespace(effective_message=message_stub(text="/hola"), effective_user=None, effective_chat=chat),
            SimpleNamespace(effective_message=message_stub(text="/hola"), effective_user=user, effective_chat=None),
            SimpleNamespace(effective_message=message_stub(text=None), effective_user=user, effective_chat=chat),
        )
        for update in cases:
            await tb._handle_command_update(update, context)

        update = SimpleNamespace(
            effective_message=message_stub(text="/hola"), effective_user=user, effective_chat=chat
        )
        db.is_user_blocked.return_value = True
        await tb._handle_command_update(update, context)
        db.is_user_blocked.return_value = False
        with patch.object(tb, "_is_user_restricted_in_message_chat", return_value=True):
            await tb._handle_command_update(update, context)
        command = SimpleNamespace(configurable_group="galeraza", list_response=False)
        with patch.object(tb, "_is_user_restricted_in_message_chat", return_value=False), patch.object(
            tb, "get_command", return_value=command
        ), patch.object(tb, "_is_command_group_disabled", return_value=True):
            await tb._handle_command_update(update, context)
        restart_command = SimpleNamespace(command_key="reiniciarbot", configurable_group=None, list_response=False)
        with patch.object(tb, "_is_user_restricted_in_message_chat", return_value=True), patch.object(
            tb, "get_command", return_value=restart_command
        ), patch.object(tb, "_cleanup_expired_restart_confirmations", AsyncMock()) as cleanup:
            await tb._handle_command_update(update, context)
        cleanup.assert_awaited_once()

    async def test_handle_command_full_paths_none_removed_and_reraise(self) -> None:
        db = MagicMock()
        db.is_user_blocked.return_value = False
        bot = MagicMock()
        bot_state = state(db)
        context = context_for(bot_state, bot)
        chat = SimpleNamespace(id=-1, type="group")
        user = SimpleNamespace(id=1, full_name="User", username="alias")
        reply_user = SimpleNamespace(id=2, full_name="Reply", username="reply")
        reply = message_stub(from_user=reply_user)
        message = message_stub(text="/hola", reply_to_message=reply)
        update = SimpleNamespace(effective_message=message, effective_user=user, effective_chat=chat)
        command = SimpleNamespace(
            configurable_group=None,
            list_response=True,
            response_parse_mode="HTML",
        )
        with patch.object(tb, "_is_user_restricted_in_message_chat", return_value=False), patch.object(
            tb, "get_command", return_value=command
        ), patch.object(tb, "_resolve_user_level", AsyncMock(return_value=UserLevel.DEV)), patch.object(
            tb, "handle_command_async", AsyncMock(return_value="response")
        ) as handle, patch.object(tb, "_send_text_response", AsyncMock()) as send:
            await tb._handle_command_update(update, context)
        kwargs = handle.await_args.kwargs
        self.assertEqual(kwargs["reply_to_user_id"], "2")
        self.assertEqual(kwargs["owner_user_id"], "1")
        self.assertTrue(callable(kwargs["send_debug_update"]))
        send.assert_awaited_once()
        self.assertEqual(send.await_args.kwargs["response_parse_mode"], "HTML")

        message.reply_to_message = None
        with patch.object(tb, "_is_user_restricted_in_message_chat", return_value=False), patch.object(
            tb, "get_command", return_value=None
        ), patch.object(tb, "handle_command_async", AsyncMock(return_value=None)) as handle:
            await tb._handle_command_update(update, context)
        self.assertIsNone(handle.await_args.kwargs["reply_to_user_id"])

        error = Forbidden("blocked")
        with patch.object(tb, "_is_user_restricted_in_message_chat", return_value=False), patch.object(
            tb, "get_command", return_value=command
        ), patch.object(tb, "_resolve_user_level", AsyncMock(return_value=UserLevel.COMMON)), patch.object(
            tb, "handle_command_async", AsyncMock(return_value="response")
        ), patch.object(tb, "_send_text_response", AsyncMock(side_effect=error)):
            await tb._handle_command_update(update, context)
        db.mark_chat_inactive.assert_called_with("-1", "send_message_failed")

        error = BadRequest("message is too old")
        with patch.object(tb, "_is_user_restricted_in_message_chat", return_value=False), patch.object(
            tb, "get_command", return_value=command
        ), patch.object(tb, "_resolve_user_level", AsyncMock(return_value=UserLevel.COMMON)), patch.object(
            tb, "handle_command_async", AsyncMock(return_value="response")
        ), patch.object(tb, "_send_text_response", AsyncMock(side_effect=error)):
            with self.assertRaises(BadRequest):
                await tb._handle_command_update(update, context)

    async def test_pagination_callback_entrypoint_all_guards(self) -> None:
        db = MagicMock()
        bot_state = state(db)
        context = context_for(bot_state)
        user = SimpleNamespace(id=1, full_name="User", username=None)
        callback = SimpleNamespace(data="", answer=AsyncMock(), message=message_stub(), from_user=user)
        await tb._callback_query_entrypoint(SimpleNamespace(callback_query=None, effective_user=user), context)
        await tb._callback_query_entrypoint(SimpleNamespace(callback_query=callback, effective_user=None), context)
        db.is_user_blocked.return_value = True
        await tb._callback_query_entrypoint(SimpleNamespace(callback_query=callback, effective_user=user), context)
        db.is_user_blocked.return_value = False
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=True):
            await tb._callback_query_entrypoint(SimpleNamespace(callback_query=callback, effective_user=user), context)
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False):
            await tb._callback_query_entrypoint(SimpleNamespace(callback_query=callback, effective_user=user), context)
        callback.data = "paginated:delete:m"
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False), patch.object(
            tb, "_handle_paginated_callback", AsyncMock(return_value="popup")
        ) as handler:
            await tb._callback_query_entrypoint(SimpleNamespace(callback_query=callback, effective_user=user), context)
        handler.assert_awaited_once()
        self.assertEqual(callback.answer.await_args.kwargs.get("text"), "popup")

    async def test_restart_callback_permissions_expiration_and_confirmation(self) -> None:
        db = MagicMock()
        db.list_restart_confirmations_before.return_value = []
        bot_state = state(db)
        bot = SimpleNamespace(delete_message=AsyncMock())
        app = SimpleNamespace(bot_data={}, create_task=MagicMock())
        context = SimpleNamespace(application=app, bot=bot)
        message = message_stub()
        callback = SimpleNamespace(message=message, data="restart:yes", answer=AsyncMock())
        user = SimpleNamespace(id=2, full_name="Other", username=None)
        confirmation = RestartConfirmation("-1", "10", "1", "2026-07-29 00:00:00")

        with patch.object(tb, "_state", return_value=bot_state):
            await tb._restart_callback_entrypoint(
                SimpleNamespace(callback_query=SimpleNamespace(message=None), effective_user=user), context
            )

        with patch.object(tb, "_state", return_value=bot_state), patch.object(
            tb, "_cleanup_expired_restart_confirmations", AsyncMock()
        ) as cleanup:
            db.get_restart_confirmation.return_value = None
            await tb._restart_callback_entrypoint(SimpleNamespace(callback_query=callback, effective_user=user), context)
            cleanup.assert_awaited_once()
        self.assertEqual(callback.answer.await_args.args[0], "mensaje eliminado")

        db.get_restart_confirmation.return_value = confirmation
        with patch.object(tb, "_state", return_value=bot_state), patch.object(
            tb, "_cleanup_expired_restart_confirmations", AsyncMock()
        ):
            await tb._restart_callback_entrypoint(SimpleNamespace(callback_query=callback, effective_user=user), context)
        self.assertEqual(callback.answer.await_args.args[0], "Usuario inválido.")

        user.id = 1
        callback.data = "restart:no"
        with patch.object(tb, "_state", return_value=bot_state), patch.object(
            tb, "_cleanup_expired_restart_confirmations", AsyncMock()
        ):
            await tb._restart_callback_entrypoint(SimpleNamespace(callback_query=callback, effective_user=user), context)
        self.assertEqual(callback.answer.await_args.args[0], "Reinicio cancelado.")

        callback.data = "restart:bad"
        with patch.object(tb, "_state", return_value=bot_state), patch.object(
            tb, "_cleanup_expired_restart_confirmations", AsyncMock()
        ):
            await tb._restart_callback_entrypoint(SimpleNamespace(callback_query=callback, effective_user=user), context)
        self.assertEqual(callback.answer.await_args.args[0], "mensaje eliminado")

        callback.data = "restart:yes"
        with patch.object(tb, "_state", return_value=bot_state), patch.object(
            tb, "_cleanup_expired_restart_confirmations", AsyncMock()
        ), patch.object(tb, "_request_restart") as request:
            await tb._restart_callback_entrypoint(SimpleNamespace(callback_query=callback, effective_user=user), context)
        request.assert_called_once_with(app)
        self.assertEqual(callback.answer.await_args.args[0], "Reinicio confirmado.")

        callback.data = "shutdown:yes"
        with patch.object(tb, "_state", return_value=bot_state), patch.object(
            tb, "_cleanup_expired_restart_confirmations", AsyncMock()
        ), patch.object(tb, "_request_shutdown") as request:
            await tb._restart_callback_entrypoint(SimpleNamespace(callback_query=callback, effective_user=user), context)
        request.assert_called_once_with(app)
        self.assertEqual(callback.answer.await_args.args[0], "Apagado confirmado.")

    async def test_config_callback_entrypoint_all_guards_and_success(self) -> None:
        db = MagicMock()
        db.get_chat_settings.return_value = SimpleNamespace(language="es", announcements_enabled=True)
        bot_state = state(db)
        context = context_for(bot_state)
        user = SimpleNamespace(id=1, full_name="User", username=None)
        callback = SimpleNamespace(data="config:main", answer=AsyncMock(), message=message_stub(), from_user=user)
        await tb._config_callback_entrypoint(SimpleNamespace(callback_query=None, effective_user=user), context)
        await tb._config_callback_entrypoint(SimpleNamespace(callback_query=callback, effective_user=None), context)
        db.is_user_blocked.return_value = True
        await tb._config_callback_entrypoint(SimpleNamespace(callback_query=callback, effective_user=user), context)
        db.is_user_blocked.return_value = False
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=True):
            await tb._config_callback_entrypoint(SimpleNamespace(callback_query=callback, effective_user=user), context)
        callback.message = None
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False):
            await tb._config_callback_entrypoint(SimpleNamespace(callback_query=callback, effective_user=user), context)
        callback.message = message_stub(chat=SimpleNamespace(id=1, type="private"))
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False):
            await tb._config_callback_entrypoint(SimpleNamespace(callback_query=callback, effective_user=user), context)
        callback.message = message_stub()
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False), patch.object(
            tb, "_resolve_user_level", AsyncMock(return_value=UserLevel.COMMON)
        ):
            await tb._config_callback_entrypoint(SimpleNamespace(callback_query=callback, effective_user=user), context)
        callback.data = "bad"
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False), patch.object(
            tb, "_resolve_user_level", AsyncMock(return_value=UserLevel.ADMIN)
        ):
            await tb._config_callback_entrypoint(SimpleNamespace(callback_query=callback, effective_user=user), context)
        callback.data = "config:main"
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False), patch.object(
            tb, "_resolve_user_level", AsyncMock(return_value=UserLevel.ADMIN)
        ), patch.object(tb, "_handle_config_callback", AsyncMock(return_value="ok")) as handler:
            await tb._config_callback_entrypoint(SimpleNamespace(callback_query=callback, effective_user=user), context)
        handler.assert_awaited_once()

    async def test_chat_member_and_error_entrypoints(self) -> None:
        db = MagicMock()
        bot_state = state(db)
        context = context_for(bot_state)
        await tb._my_chat_member_entrypoint(SimpleNamespace(my_chat_member=None), context)
        member_update = SimpleNamespace(
            chat=SimpleNamespace(id=-1, type="group", title="G"),
            new_chat_member=SimpleNamespace(user=SimpleNamespace(id=2), status=ChatMember.MEMBER),
            from_user=None,
        )
        await tb._my_chat_member_entrypoint(SimpleNamespace(my_chat_member=member_update), context)
        member_update.new_chat_member.user.id = 99
        await tb._my_chat_member_entrypoint(SimpleNamespace(my_chat_member=member_update), context)
        member_update.from_user = SimpleNamespace(id=1)
        member_update.new_chat_member.status = ChatMember.LEFT
        await tb._my_chat_member_entrypoint(SimpleNamespace(my_chat_member=member_update), context)
        db.mark_chat_inactive.assert_called_with("-1", ChatMember.LEFT)

        application = SimpleNamespace(bot_data={}, stop_running=MagicMock())
        error_context = SimpleNamespace(error=None, application=application, bot=MagicMock())
        await tb._handle_error(None, error_context)
        error_context.error = Conflict("conflict")
        await tb._handle_error(None, error_context)
        application.stop_running.assert_called_once()
        application.bot_data["settings"] = settings()
        error_context.error = RuntimeError("failure")
        with patch.object(tb, "_send_unhandled_error_event", AsyncMock()) as send:
            await tb._handle_error({"u": 1}, error_context)
        send.assert_awaited_once()

        error_context.error = NetworkError("httpx.ReadError")
        with patch.object(tb, "_send_unhandled_error_event", AsyncMock()) as send:
            await tb._handle_error(None, error_context)
        send.assert_not_awaited()

        error_context.error = BadRequest(
            "Query is too old and response timeout expired or query ID is invalid"
        )
        with patch.object(tb, "_send_unhandled_error_event", AsyncMock()) as send, patch.object(
            tb.logger, "exception"
        ) as log_exception:
            await tb._handle_error({"callback_query": {}}, error_context)
        send.assert_not_awaited()
        log_exception.assert_not_called()

        for source in ("update", "job", "coroutine"):
            scoped_context = SimpleNamespace(
                error=NetworkError("network failure"),
                application=application,
                bot=MagicMock(),
                job=object() if source == "job" else None,
                coroutine=object() if source == "coroutine" else None,
            )
            scoped_update = {"u": 2} if source == "update" else None
            with patch.object(tb, "_send_unhandled_error_event", AsyncMock()) as send:
                await tb._handle_error(scoped_update, scoped_context)
            send.assert_awaited_once()

    def test_display_and_restriction_helpers(self) -> None:
        self.assertIsNone(tb._display_name(None))
        self.assertEqual(tb._display_name(User(1, "First", False, username="alias")), "First")
        db = MagicMock()
        self.assertFalse(tb._is_user_restricted_in_message_chat(db, message_stub(chat=SimpleNamespace(id=1, type="private")), "1"))
        db.is_user_restricted_in_chat.return_value = True
        self.assertTrue(tb._is_user_restricted_in_message_chat(db, message_stub(), "1"))
        self.assertFalse(tb._is_user_restricted_in_callback_chat(db, SimpleNamespace(message=None), "1"))
        self.assertTrue(tb._is_user_restricted_in_callback_chat(db, SimpleNamespace(message=message_stub()), "1"))


class PayloadAndModerationCompleteTests(unittest.IsolatedAsyncioTestCase):
    def test_trigger_payload_all_remaining_types_and_optional_fields(self) -> None:
        self.assertIsNone(tb._trigger_payload_from_message(None))
        self.assertEqual(tb._trigger_payload_from_message(message_stub(text="text")), TriggerPayload(text="text"))
        cases = (
            ("audio", SimpleNamespace(file_id="f")),
            ("voice", SimpleNamespace(file_id="f")),
            ("animation", SimpleNamespace(file_id="f")),
        )
        for field, media in cases:
            payload = tb._trigger_payload_from_message(message_stub(**{field: media}))
            self.assertEqual(payload.media_type, field)
        contact = SimpleNamespace(phone_number="1", first_name="F", last_name=None, vcard=None)
        self.assertNotIn("last_name", tb._trigger_payload_from_message(message_stub(contact=contact)).data)
        location = SimpleNamespace(latitude=1, longitude=2, horizontal_accuracy=None)
        self.assertEqual(tb._trigger_payload_from_message(message_stub(location=location)).data, {"latitude": 1, "longitude": 2})
        venue = SimpleNamespace(
            location=location,
            title="T",
            address="A",
            foursquare_id=None,
            foursquare_type=None,
            google_place_id=None,
            google_place_type=None,
        )
        self.assertEqual(tb._trigger_payload_from_message(message_stub(venue=venue)).data["title"], "T")
        poll = SimpleNamespace(
            question="Q", options=[SimpleNamespace(text="A")], is_anonymous=True,
            type="quiz", allows_multiple_answers=False, correct_option_id=None, explanation=None,
        )
        self.assertNotIn("correct_option_id", tb._trigger_payload_from_message(message_stub(poll=poll)).data)
        poll.correct_option_id = 0
        poll.explanation = "Because"
        payload = tb._trigger_payload_from_message(message_stub(poll=poll))
        self.assertEqual(payload.data["correct_option_id"], 0)
        self.assertEqual(payload.data["explanation"], "Because")

    async def test_moderation_all_guards_video_and_download_error(self) -> None:
        disabled = SimpleNamespace(enabled=False)
        self.assertEqual(await tb._moderate_trigger_payload(MagicMock(), disabled, TriggerPayload()), TriggerModerationResult.SKIPPED)
        moderator = SimpleNamespace(enabled=True, moderate_image=AsyncMock(), moderate_video=AsyncMock(return_value=TriggerModerationResult.SAFE))
        self.assertEqual(await tb._moderate_trigger_payload(MagicMock(), moderator, TriggerPayload(media_type="audio")), TriggerModerationResult.SKIPPED)
        self.assertEqual(await tb._moderate_trigger_payload(MagicMock(), moderator, TriggerPayload(media_type="video", mime_type="video/mp4")), TriggerModerationResult.ERROR)
        downloaded = bytearray(b"video")
        bot = SimpleNamespace(get_file=AsyncMock(return_value=SimpleNamespace(download_as_bytearray=AsyncMock(return_value=downloaded))))
        result = await tb._moderate_trigger_payload(bot, moderator, TriggerPayload(media_type="video", mime_type="video/mp4", file_id="f"))
        self.assertEqual(result, TriggerModerationResult.SAFE)
        self.assertFalse(downloaded)
        moderator.moderate_video.assert_awaited_once()
        bot.get_file.side_effect = BadRequest("file")
        self.assertEqual(
            await tb._moderate_trigger_payload(bot, moderator, TriggerPayload(media_type="photo", mime_type="image/jpeg", file_id="f")),
            TriggerModerationResult.ERROR,
        )


class GalerazaExpenseAndConfigTests(unittest.IsolatedAsyncioTestCase):
    async def test_award_galeraza_all_paths(self) -> None:
        db = MagicMock()
        private = message_stub(chat=SimpleNamespace(id=1, type="private"))
        await tb._maybe_award_daily_galeraza(db, private, "1")
        message = message_stub()
        db.is_command_group_enabled.return_value = False
        await tb._maybe_award_daily_galeraza(db, message, "1")
        db.is_command_group_enabled.return_value = True
        db.try_award_daily_galeraza.return_value = False
        await tb._maybe_award_daily_galeraza(db, message, "1")
        db.try_award_daily_galeraza.return_value = True
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        await tb._maybe_award_daily_galeraza(db, message, "1")
        message.reply_text.assert_awaited_once()

        message.reply_text.side_effect = TimedOut()
        with self.assertRaises(TimedOut):
            await tb._maybe_award_daily_galeraza(db, message, "1")
        self.assertEqual(message.reply_text.await_count, 2)
        self.assertEqual(db.try_award_daily_galeraza.call_count, 3)

    async def test_send_galerazas_single_multi_empty_id_and_failure(self) -> None:
        db = MagicMock()
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        message = message_stub()
        result = SimpleNamespace(message_id=10, edit_text=AsyncMock())
        message.reply_text.return_value = result
        db.get_galeraza_scores.return_value = []
        self.assertTrue(await tb._send_galerazas(db, message, "1"))
        db.save_paginated_message_state.assert_not_called()

        page = SimpleNamespace(text="Title\nrow", page=1, total_pages=2)
        with patch.object(galeraza_handlers, "render_galeraza_page", return_value=page):
            self.assertTrue(await tb._send_galerazas(db, message, "1"))
        db.save_paginated_message_state.assert_called()
        result.edit_text.assert_awaited()

        result.message_id = ""
        db.save_paginated_message_state.reset_mock()
        with patch.object(galeraza_handlers, "render_galeraza_page", return_value=page):
            self.assertTrue(await tb._send_galerazas(db, message, "1"))
        db.save_paginated_message_state.assert_not_called()
        message.reply_text.side_effect = BadRequest("send")
        self.assertFalse(await tb._send_galerazas(db, message, "1"))

    async def test_send_text_response_truncation_single_and_pages(self) -> None:
        db = MagicMock()
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        message = message_stub()
        bot = MagicMock()
        with patch.object(tb, "_send_log_event", AsyncMock()) as log:
            await tb._send_text_response(db, message, "x" * 5000, "1", "command", False, bot, "-10")
        self.assertEqual(len(message.reply_text.await_args.args[0]), 4096)
        log.assert_awaited_once()

        message.reply_text.reset_mock()
        message.reply_text.return_value = SimpleNamespace(message_id=1, edit_text=AsyncMock())
        await tb._send_text_response(db, message, "", "1", "command", True, bot, "-10")
        message.reply_text.assert_awaited_once()
        result = SimpleNamespace(message_id=2, edit_text=AsyncMock())
        message.reply_text.return_value = result
        long_list = "Header\n" + "\n".join("row " + ("x" * 100) for _ in range(100))
        await tb._send_text_response(db, message, long_list, "1", "command", True, bot, "-10")
        db.save_paginated_message_state.assert_called()
        result.edit_text.assert_awaited_once()
        result.message_id = ""
        db.save_paginated_message_state.reset_mock()
        await tb._send_text_response(db, message, long_list, "1", "command", True, bot, "-10")
        db.save_paginated_message_state.assert_not_called()

        message.reply_text.side_effect = TimedOut()
        with self.assertRaises(TimedOut):
            await tb._send_text_response(
                db,
                message,
                "Triggers:\n\n- uno",
                "1",
                "triggers",
                True,
                bot,
                "-10",
            )

        message.reply_text.side_effect = None
        message.reply_text.return_value = SimpleNamespace(message_id=3, edit_text=AsyncMock())
        await tb._send_text_response(db, message, "Triggers:\n\n- uno", "1", "triggers", True, bot, "-10")
        self.assertEqual(message.reply_text.await_args.kwargs["entities"][0].type, "bold")

        result = SimpleNamespace(message_id=4, edit_text=AsyncMock())
        message.reply_text.return_value = result
        html_list = "<b>Reglas</b>\n" + "\n".join(
            f"detalle {index} " + ("x" * 100) for index in range(100)
        )
        await tb._send_text_response(
            db,
            message,
            html_list,
            "1",
            "command",
            True,
            bot,
            "-10",
            "HTML",
        )
        self.assertEqual(message.reply_text.await_args.kwargs["parse_mode"], "HTML")
        self.assertEqual(result.edit_text.await_args.kwargs["parse_mode"], "HTML")

    async def test_report_submit_status_and_sync_expenses(self) -> None:
        db = MagicMock()
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        message = message_stub(chat=SimpleNamespace(id=-1, type="group", title=None))
        user = User(1, "First", False)
        self.assertFalse(await tb._send_report(db, MagicMock(), None, message, user, "bug"))
        with patch.object(tb, "_send_log_text_with_truncation", AsyncMock(return_value=True)) as send:
            self.assertTrue(await tb._send_report(db, MagicMock(), "-10", message, user, "bug"))
        self.assertIn("username=-", send.await_args.args[2])

        expense = Expense(1, "-1", "1", None, None, 100, "ARS", "cash", "box", "food", "pending", None, "now", None)
        db.add_expense.return_value = expense
        writer = MagicMock()
        writer.write_expense.return_value = ExpenseSheetWriteResult(True)
        provider = MagicMock()
        provider.binance_usdt_sell_rate.return_value = ExchangeRateQuote(
            Decimal("1600"), datetime(2026, 7, 22, tzinfo=timezone.utc)
        )
        draft = ExpenseDraft(
            100,
            "ARS",
            "Efectivo",
            "Otros",
            "Lucas",
            "food",
            date(2026, 7, 22),
            0,
            ExpenseMovement.PURCHASE,
            True,
            True,
        )
        result = await tb._submit_expense(db, writer, provider, message, user, draft)
        self.assertTrue(result.synced)
        db.mark_expense_synced.assert_called_with(1, None, None, None)
        writer.write_expense.return_value = ExpenseSheetWriteResult(False, "api")
        writer.is_configured.return_value = False
        result = await tb._submit_expense(db, writer, provider, message, user, draft)
        self.assertFalse(result.synced)
        self.assertFalse(result.configured)
        db.mark_expense_failed.assert_called_with(1, "api", None, None, None)

        historical = replace(draft, occurred_on=date(2026, 7, 21))
        self.assertEqual(
            (await tb._submit_expense(db, writer, provider, message, user, historical)).error,
            "historical_rate_required",
        )
        provider.binance_usdt_sell_rate.side_effect = ExchangeRateError("offline")
        self.assertEqual(
            (await tb._submit_expense(db, writer, provider, message, user, draft)).error,
            "exchange_rate_unavailable",
        )
        provider.binance_usdt_sell_rate.side_effect = None

        late_utc_message = message_stub(
            chat=message.chat,
            date=datetime(2026, 7, 22, 2, tzinfo=timezone.utc),
        )
        local_date_draft = replace(draft, occurred_on=date(2026, 7, 21))
        writer.is_configured.return_value = True
        writer.write_expense.return_value = ExpenseSheetWriteResult(True)
        self.assertTrue(
            (
                await tb._submit_expense(
                    db, writer, provider, late_utc_message, user, local_date_draft
                )
            ).synced
        )

        writer.is_configured.return_value = True
        writer.write_expense.return_value = ExpenseSheetWriteResult(True)
        provider.binance_usdt_sell_rate.reset_mock()
        usd = replace(draft, currency="USD", installments=1, usd_rate_override=None)
        self.assertTrue((await tb._submit_expense(db, writer, provider, message, user, usd)).synced)
        provider.binance_usdt_sell_rate.assert_not_called()
        manual = replace(draft, usd_rate_override=Decimal("1599.25"))
        self.assertTrue((await tb._submit_expense(db, writer, provider, message, user, manual)).synced)
        provider.binance_usdt_sell_rate.assert_not_called()

        writer.write_expense.return_value = ExpenseSheetWriteResult(True, month_created=True)
        with patch.object(tb, "_sync_pending_expenses", AsyncMock()) as sync:
            self.assertTrue((await tb._submit_expense(db, writer, provider, message, user, draft)).synced)
        sync.assert_awaited_once()
        no_open = replace(draft, opens_cashflow_month=False)
        with patch.object(tb, "_sync_pending_expenses", AsyncMock()) as sync:
            self.assertTrue((await tb._submit_expense(db, writer, provider, message, user, no_open)).synced)
        sync.assert_not_awaited()

        writer.is_configured.return_value = False
        writer.is_ready.return_value = False
        db.count_pending_expenses.return_value = 2
        status = tb._build_expense_sheet_status(db, writer, "-1")
        self.assertIsNone(status.worksheet_name)
        writer.is_configured.return_value = True
        writer.worksheet_name = "Tab"
        self.assertEqual(tb._build_expense_sheet_status(db, writer, "-1").worksheet_name, "Tab")

        writer.is_configured.return_value = False
        self.assertFalse((await tb._sync_pending_expenses(db, writer, message)).configured)
        writer.is_configured.return_value = True
        expense2 = replace(expense, expense_id=2, username="alias", display_name="Name")
        db.list_pending_expenses.return_value = [expense, expense2]
        writer.write_expense.side_effect = [
            ExpenseSheetWriteResult(True),
            ExpenseSheetWriteResult(False, "fail"),
        ]
        result = await tb._sync_pending_expenses(db, writer, message)
        self.assertEqual((result.synced_count, result.failed_count, result.last_error), (1, 1, "fail"))
        writer.add_card_closing.return_value = SimpleNamespace(added=True)
        self.assertTrue((await tb._add_card_closing(writer, date(2026, 8, 28))).added)

    async def test_send_config_menu_and_every_config_action(self) -> None:
        db = MagicMock()
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        message = message_stub()
        self.assertTrue(await tb._send_config_menu(db, message))
        message.reply_text.side_effect = BadRequest("send")
        self.assertFalse(await tb._send_config_menu(db, message))
        message.reply_text.side_effect = None

        self.assertIn("eliminado", (await tb._handle_config_callback(db, message, ("close",))).lower())
        for parsed in (("main",), ("language",), ("commands",)):
            self.assertIsNone(await tb._handle_config_callback(db, message, parsed))
        private_message = message_stub(chat=SimpleNamespace(id=-1, type="private"))
        self.assertIsNone(await tb._handle_config_callback(db, private_message, ("commands",)))
        self.assertIsNone(await tb._handle_config_callback(db, message, ("lang", "xx")))
        self.assertIsNone(await tb._handle_config_callback(db, message, ("lang", "es")))
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        self.assertIn("updated", (await tb._handle_config_callback(db, message, ("lang", "en"))).lower())
        db.get_chat_settings.return_value = SimpleNamespace(language="es", announcements_enabled=True)
        self.assertIsNone(await tb._handle_config_callback(db, message, ("announcements",)))
        self.assertIsNone(await tb._handle_config_callback(db, message, ("setannouncements", "1")))
        self.assertIn("actualizada", (await tb._handle_config_callback(db, message, ("setannouncements", "0"))).lower())
        self.assertIsNone(await tb._handle_config_callback(db, message, ("command", "unknown")))
        db.is_command_group_enabled.return_value = True
        self.assertIsNone(await tb._handle_config_callback(db, message, ("command", "galeraza")))
        self.assertIsNone(await tb._handle_config_callback(db, message, ("set", "unknown", "1")))
        self.assertIsNone(await tb._handle_config_callback(db, message, ("set", "galeraza", "1")))
        db.is_command_group_enabled.return_value = False
        self.assertIn("actualizada", (await tb._handle_config_callback(db, message, ("set", "galeraza", "1"))).lower())
        self.assertIsNone(await tb._handle_config_callback(db, message, ("unknown",)))

    async def test_broadcast_announcements_updates_only_definitive_failures(self) -> None:
        db = MagicMock()
        db.list_active_chats.return_value = [
            SimpleNamespace(chat_id="-1"),
            SimpleNamespace(chat_id="-2"),
            SimpleNamespace(chat_id="-3"),
        ]
        db.get_chat_settings.side_effect = [
            SimpleNamespace(language="es", announcements_enabled=True),
            SimpleNamespace(language="en", announcements_enabled=False),
            SimpleNamespace(language="es", announcements_enabled=True),
            SimpleNamespace(language="es", announcements_enabled=True),
        ]
        bot = SimpleNamespace(send_message=AsyncMock(side_effect=[None, Forbidden("blocked"), None]))

        result = await tb._broadcast_announcement(db, bot, "Hola", "-11")

        self.assertEqual((result.sent_count, result.skipped_count, result.inactive_count, result.failed_count), (1, 1, 1, 0))
        self.assertTrue(result.announcement_channel_sent)
        db.mark_chat_inactive.assert_called_once_with("-3", "announcement_send_failed")
        self.assertTrue(bot.send_message.await_args_list[0].kwargs["text"].endswith("/config."))
        self.assertTrue(bot.send_message.await_args_list[0].kwargs["link_preview_options"].is_disabled)

        db.list_active_chats.return_value = [SimpleNamespace(chat_id="-1")]
        db.get_chat_settings.side_effect = [
            SimpleNamespace(language="es", announcements_enabled=True),
            SimpleNamespace(language="es", announcements_enabled=True),
        ]
        bot.send_message = AsyncMock(side_effect=[TimedOut(), BadRequest("channel")])
        result = await tb._broadcast_announcement(db, bot, "Hola", "-11")
        self.assertEqual(result.failed_count, 1)
        self.assertFalse(result.announcement_channel_sent)

        self.assertTrue(tb.announcement_fits("Hola", tb.TELEGRAM_MESSAGE_LIMIT_CHARS))
        self.assertFalse(tb.announcement_fits("x" * tb.TELEGRAM_MESSAGE_LIMIT_CHARS, tb.TELEGRAM_MESSAGE_LIMIT_CHARS))
        self.assertTrue((await tb._broadcast_announcement(db, bot, "x" * tb.TELEGRAM_MESSAGE_LIMIT_CHARS, "-11")).too_long)

        db.list_active_chats.return_value = [SimpleNamespace(chat_id="-11")]
        db.get_chat_settings.side_effect = [SimpleNamespace(language="es", announcements_enabled=True)]
        bot.send_message = AsyncMock()
        result = await tb._broadcast_announcement(db, bot, "Hola", "-11")
        self.assertEqual(result.skipped_count, 0)
        self.assertTrue(result.announcement_channel_sent)
        self.assertTrue(bot.send_message.await_args.kwargs["link_preview_options"].is_disabled)

        db.list_active_chats.return_value = []
        result = await tb._broadcast_announcement(db, bot, "Hola", None)
        self.assertFalse(result.announcement_channel_sent)


class PaginationAndChatHelpersTests(unittest.IsolatedAsyncioTestCase):
    def paginated_state(self, **changes) -> PaginatedMessageState:
        base = PaginatedMessageState("-1", "10", "command", "1", '{"header":"H","lines":["x"]}', False, 1, "2026-07-22 00:00:00")
        return replace(base, **changes)

    async def test_paginated_callback_missing_expired_permissions_and_actions(self) -> None:
        db = MagicMock()
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        user = SimpleNamespace(id=1)
        message = message_stub()
        callback = SimpleNamespace(from_user=user, message=None)
        self.assertIsNone(await tb._handle_paginated_callback(callback, db, frozenset(), ("page", "10", "1")))
        callback.message = message
        db.get_paginated_message_state.return_value = None
        with patch.object(tb, "_delete_paginated_message", AsyncMock()) as delete:
            self.assertIn("eliminado", await tb._handle_paginated_callback(callback, db, frozenset(), ("page", "10", "1")))
        delete.assert_awaited_once()
        db.get_paginated_message_state.return_value = self.paginated_state()
        with patch.object(tb, "_is_paginated_state_expired", return_value=True), patch.object(
            tb, "_delete_paginated_message", AsyncMock()
        ):
            self.assertIn("eliminado", await tb._handle_paginated_callback(callback, db, frozenset(), ("page", "10", "1")))

        with patch.object(tb, "_is_paginated_state_expired", return_value=False), patch.object(
            tb, "_edit_paginated_message", AsyncMock()
        ) as edit:
            self.assertIn("todos", await tb._handle_paginated_callback(callback, db, frozenset(), ("unlock", "10", None)))
            db.get_paginated_message_state.return_value = self.paginated_state(unlocked=True)
            self.assertIn("deshabilitado", await tb._handle_paginated_callback(callback, db, frozenset(), ("unlock", "10", None)))
        self.assertEqual(edit.await_count, 2)

        callback.from_user = SimpleNamespace(id=2)
        db.get_paginated_message_state.return_value = self.paginated_state()
        with patch.object(tb, "_is_paginated_state_expired", return_value=False):
            self.assertIsNone(await tb._handle_paginated_callback(callback, db, frozenset(), ("unlock", "10", None)))
            self.assertIsNone(await tb._handle_paginated_callback(callback, db, frozenset(), ("delete", "10", None)))
            self.assertIsNone(await tb._handle_paginated_callback(callback, db, frozenset(), ("page", "10", None)))
        db.get_paginated_message_state.return_value = self.paginated_state(unlocked=True)
        with patch.object(tb, "_is_paginated_state_expired", return_value=False), patch.object(
            tb, "_edit_paginated_message", AsyncMock()
        ) as edit:
            self.assertIsNone(await tb._handle_paginated_callback(callback, db, frozenset(), ("page", "10", "bad")))
            self.assertIsNone(await tb._handle_paginated_callback(callback, db, frozenset(), ("page", "10", "1")))
            self.assertIsNone(await tb._handle_paginated_callback(callback, db, frozenset(), ("page", "10", "2")))
            self.assertIsNone(await tb._handle_paginated_callback(callback, db, frozenset(), ("unknown", "10", None)))
        edit.assert_awaited_once()
        callback.from_user = SimpleNamespace(id=1)
        with patch.object(tb, "_is_paginated_state_expired", return_value=False), patch.object(
            tb, "_delete_paginated_message", AsyncMock()
        ) as delete:
            self.assertIn("eliminado", await tb._handle_paginated_callback(callback, db, frozenset(), ("delete", "10", None)))
        delete.assert_awaited_once()

    async def test_delete_cleanup_expiration_and_edit(self) -> None:
        db = MagicMock()
        message = message_stub()
        await tb._delete_paginated_message(db, message, "10")
        message.delete.side_effect = BadRequest("delete")
        await tb._delete_paginated_message(db, message, "10")
        bot = SimpleNamespace(delete_message=AsyncMock())
        await tb._delete_paginated_message_by_id(db, bot, -1, "10")
        bot.delete_message.side_effect = BadRequest("delete")
        await tb._delete_paginated_message_by_id(db, bot, -1, "10")
        db.list_paginated_message_states_before.return_value = []
        await tb._cleanup_old_paginated_messages(db, bot)
        db.list_paginated_message_states_before.return_value = [self.paginated_state()]
        with patch.object(tb, "_delete_paginated_message_by_id", AsyncMock()) as delete:
            await tb._cleanup_old_paginated_messages(db, bot)
        delete.assert_awaited_once()
        self.assertRegex(tb._paginated_metadata_cutoff(), r"^\d{4}-")
        self.assertFalse(tb._is_paginated_state_expired("bad"))
        self.assertFalse(tb._is_paginated_state_expired(datetime.now(timezone.utc).replace(tzinfo=None).isoformat()))
        old = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
        recent = datetime.now(timezone.utc).isoformat()
        self.assertTrue(tb._is_paginated_state_expired(old))
        self.assertFalse(tb._is_paginated_state_expired(recent))

        restart_message = message_stub()
        db.list_restart_confirmations_before.return_value = []
        await tb._cleanup_expired_restart_confirmations(db, bot)
        db.list_restart_confirmations_before.return_value = [
            RestartConfirmation("-1", "10", "1", "2026-07-29 00:00:00")
        ]
        with patch.object(tb, "_delete_restart_confirmation_by_id", AsyncMock()) as delete:
            await tb._cleanup_expired_restart_confirmations(db, bot)
        delete.assert_awaited_once()
        await tb._delete_restart_confirmation_message(db, restart_message)
        restart_message.delete.side_effect = BadRequest("delete")
        await tb._delete_restart_confirmation_message(db, restart_message)
        await tb._delete_restart_confirmation_by_id(db, bot, -1, "10")
        bot.delete_message.side_effect = BadRequest("delete")
        await tb._delete_restart_confirmation_by_id(db, bot, -1, "10")
        bot.delete_message.side_effect = None

        created = message_stub()
        created.reply_text.return_value = SimpleNamespace(message_id=55)
        self.assertTrue(await tb._create_restart_confirmation(db, created, "1"))
        self.assertTrue(await tb._create_restart_confirmation(db, created, "1", shutdown=True))
        self.assertEqual(created.reply_text.await_args.kwargs["reply_markup"].inline_keyboard[0][0].callback_data, "shutdown:yes")
        created.reply_text.side_effect = BadRequest("send")
        self.assertFalse(await tb._create_restart_confirmation(db, created, "1"))

        db.get_paginated_message_state.return_value = None
        await tb._edit_paginated_message(db, message, "10", 1, False)
        db.get_paginated_message_state.return_value = self.paginated_state()
        message.edit_text.side_effect = None
        await tb._edit_paginated_message(db, message, "10", 1, False)
        db.get_paginated_message_state.return_value = self.paginated_state(list_type="galeraza")
        await tb._edit_paginated_message(db, message, "10", 1, True)
        self.assertIn("entities", message.edit_text.await_args.kwargs)
        db.get_paginated_message_state.return_value = self.paginated_state(
            list_type="galeraza",
            content_json='{"pages":["Tabla de Galerazas\\n\\n1. A (1) => 9","Tabla de Galerazas\\n\\n2. B (2) => 8"]}',
        )
        await tb._edit_paginated_message(db, message, "10", 2, False)
        self.assertEqual(message.edit_text.await_args.kwargs["text"], "Tabla de Galerazas\n\n2. B (2) => 8")

    async def test_restart_request_waits_for_pending_updates(self) -> None:
        application = SimpleNamespace(bot_data={}, create_task=MagicMock())
        tb._request_restart(application)
        self.assertTrue(application.bot_data["restart_requested"])
        task = application.create_task.call_args.args[0]
        task.close()
        tb._request_restart(application)
        self.assertEqual(application.create_task.call_count, 1)

        shutdown_application = SimpleNamespace(bot_data={}, create_task=MagicMock())
        tb._request_shutdown(shutdown_application)
        self.assertEqual(shutdown_application.bot_data["power_requested"], "shutdown")
        shutdown_task = shutdown_application.create_task.call_args.args[0]
        shutdown_task.close()
        tb._request_shutdown(shutdown_application)
        self.assertEqual(shutdown_application.create_task.call_count, 1)

        queue = SimpleNamespace(join=AsyncMock())
        updater = SimpleNamespace(stop=AsyncMock())
        application = SimpleNamespace(update_queue=queue, updater=updater, stop_running=MagicMock())
        await tb._restart_after_pending_updates(application)
        updater.stop.assert_awaited_once()
        queue.join.assert_awaited_once()
        application.stop_running.assert_called_once()

        updater.stop.side_effect = RuntimeError("already stopped")
        await tb._restart_after_pending_updates(application)
        self.assertEqual(updater.stop.await_count, 2)

        timeout_application = SimpleNamespace(
            update_queue=SimpleNamespace(join=AsyncMock(side_effect=TimeoutError)),
            updater=SimpleNamespace(stop=AsyncMock()),
            bot=MagicMock(),
            bot_data={"settings": settings()},
            stop_running=MagicMock(),
        )
        with patch.object(tb, "_send_log_event", AsyncMock()) as send_log, patch.object(
            tb.os, "_exit"
        ) as exit_process:
            await tb._stop_after_pending_updates(timeout_application, "shutdown")
        send_log.assert_awaited_once()
        exit_process.assert_called_once_with(0)

        with patch.object(tb, "_send_log_event", AsyncMock()), patch.object(
            tb, "_mark_panel_restart_pending"
        ) as mark_restart, patch.object(tb.os, "execv") as restart_process, patch.object(tb.os, "_exit") as exit_process:
            await tb._stop_after_pending_updates(timeout_application, "restart")
        mark_restart.assert_called_once()
        restart_process.assert_called_once_with(tb.sys.executable, [tb.sys.executable, *tb.sys.argv])
        exit_process.assert_called_once_with(0)

    def test_chat_registration_migration_added_removed(self) -> None:
        db = MagicMock()
        tb._register_chat_from_message(message_stub(chat=None), db)
        message = message_stub()
        tb._register_chat_from_message(message, db)
        self.assertFalse(tb._handle_chat_migration(message_stub(chat=None), db))
        self.assertFalse(tb._handle_chat_migration(message, db))
        db.migrate_chat_id.return_value = True
        self.assertTrue(tb._handle_chat_migration(message_stub(migrate_to_chat_id=-100), db))
        db.migrate_chat_id.return_value = False
        self.assertFalse(tb._handle_chat_migration(message_stub(migrate_from_chat_id=-1), db))
        tb._register_bot_added_event(message_stub(chat=None), db, "99")
        tb._register_bot_added_event(message_stub(from_user=None), db, "99")
        tb._register_bot_added_event(message_stub(from_user=SimpleNamespace(id=1), new_chat_members=[]), db, "99")
        adder = SimpleNamespace(id=1, full_name="Adder", username=None)
        bot_user = SimpleNamespace(id=99)
        tb._register_bot_added_event(message_stub(from_user=adder, new_chat_members=[bot_user]), db, "99")
        tb._register_bot_removed_event(message_stub(chat=None), db, "99")
        tb._register_bot_removed_event(message_stub(left_chat_member=None), db, "99")
        tb._register_bot_removed_event(message_stub(left_chat_member=SimpleNamespace(id=99)), db, "99")
        db.mark_chat_inactive.assert_called_with("-1", "left_chat_member")


class PermissionsLoggingBackupAndMiscTests(unittest.IsolatedAsyncioTestCase):
    async def test_levels_admin_permissions_and_roulette_failures(self) -> None:
        db = MagicMock()
        chat = SimpleNamespace(id=-1, type="group")
        bot = SimpleNamespace(get_chat_administrators=AsyncMock(return_value=[]), get_chat_member=AsyncMock())
        self.assertEqual(await tb._resolve_user_level("1", chat, db, bot, frozenset({"1"})), UserLevel.DEV)
        db.get_chat_added_by_user_id.return_value = "2"
        self.assertEqual(await tb._resolve_user_level("2", chat, db, bot, frozenset()), UserLevel.ADMIN)
        db.get_chat_added_by_user_id.return_value = None
        bot.get_chat_administrators.return_value = [SimpleNamespace(user=SimpleNamespace(id=3))]
        self.assertEqual(await tb._resolve_user_level("3", chat, db, bot, frozenset()), UserLevel.ADMIN)
        self.assertEqual(await tb._resolve_user_level("4", SimpleNamespace(id=1, type="private"), db, bot, frozenset()), UserLevel.COMMON)
        self.assertFalse(tb._is_command_group_disabled(db, chat, None))
        self.assertFalse(tb._is_command_group_disabled(db, SimpleNamespace(id=1, type="private"), "x"))
        db.is_command_group_enabled.return_value = False
        self.assertTrue(tb._is_command_group_disabled(db, chat, "x"))
        bot.get_chat_administrators.side_effect = BadRequest("admins")
        self.assertFalse(await tb._is_chat_admin(-1, "1", bot))

        bot.get_chat_member.side_effect = BadRequest("member")
        self.assertFalse(await tb._bot_can_ban_members(bot, -1, "99"))
        bot.get_chat_member.side_effect = None
        bot.get_chat_member.return_value = SimpleNamespace(status=ChatMember.OWNER)
        self.assertTrue(await tb._bot_can_ban_members(bot, -1, "99"))
        bot.get_chat_member.return_value = SimpleNamespace(status=ChatMember.MEMBER)
        self.assertFalse(await tb._bot_can_ban_members(bot, -1, "99"))
        bot.ban_chat_member = AsyncMock()
        bot.get_chat_member.return_value = SimpleNamespace(status=ChatMember.ADMINISTRATOR)
        self.assertEqual(await tb._resolve_russian_roulette_hit(bot, -1, "2", "99", frozenset()), tb.RussianRouletteHitResult.ADMIN_IMMUNE)
        bot.get_chat_member.side_effect = BadRequest("hit")
        self.assertEqual(await tb._resolve_russian_roulette_hit(bot, -1, "2", "99", frozenset()), tb.RussianRouletteHitResult.FAILED)

    async def test_logging_unhandled_announcement_and_status_paths(self) -> None:
        bot = SimpleNamespace(send_message=AsyncMock(), send_document=AsyncMock())
        with patch.object(tb, "_send_log_text_with_truncation", AsyncMock()) as send:
            try:
                raise RuntimeError("x" * 3000)
            except RuntimeError as exc:
                await tb._send_unhandled_error_event(bot, "-10", exc, None)
        error_text = send.await_args.args[2]
        self.assertTrue(error_text.startswith("RuntimeError: "))
        self.assertNotIn("Error no handleado", error_text)
        debug_text = bot.send_document.await_args.kwargs["document"].getvalue().decode("utf-8")
        self.assertIn("Error no handleado", debug_text)
        self.assertIn("Update JSON", debug_text)
        with patch.object(tb, "save_logging_status") as status:
            self.assertFalse(await tb._send_log_event(bot, None, "x"))
        status.assert_called_once()
        with patch.object(tb, "save_logging_status") as status:
            self.assertTrue(await tb._send_log_text_with_truncation(bot, "-10", "x" * 5000, "truncated"))
        self.assertEqual(bot.send_message.await_count, 2)
        status.assert_called_with(True, "Canal de logging accesible.")
        bot.send_message.reset_mock(side_effect=True)
        bot.send_message.side_effect = BadRequest("log")
        with patch.object(tb, "save_logging_status"):
            self.assertFalse(await tb._send_log_text_with_truncation(bot, "bad id", "x"))

        self.assertFalse(await tb._send_announcement(bot, None, "x"))
        bot.send_message.side_effect = None
        self.assertTrue(await tb._send_announcement(bot, "-11", "short"))
        self.assertTrue(bot.send_message.await_args.kwargs["link_preview_options"].is_disabled)
        with patch.object(tb, "_send_log_event", AsyncMock()) as log:
            self.assertTrue(await tb._send_announcement(bot, "-11", "x" * 5000, "-10", "es"))
        log.assert_awaited_once()
        bot.send_message.side_effect = BadRequest("announcement")
        self.assertFalse(await tb._send_announcement(bot, "-11", "x"))

    async def test_backup_debug_leave_and_misc_helpers(self) -> None:
        db = MagicMock()
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        message = message_stub()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "backup.sqlite3"
            path.write_bytes(b"x")
            db.create_backup.return_value = path
            result = await tb._create_and_send_backup(db, message)
            self.assertTrue(result.sent)
            with patch.object(tb, "TELEGRAM_DOCUMENT_UPLOAD_LIMIT_BYTES", 0):
                self.assertFalse((await tb._create_and_send_backup(db, message)).sent)

        with patch.object(tb, "_serialize_update", return_value="x" * 5000):
            self.assertTrue(await tb._send_debug_update(db, message, None))
        self.assertEqual(message.reply_document.await_args.kwargs["filename"], "Debug de la update sin id")
        self.assertEqual(json.loads(tb._serialize_update(None)), None)
        self.assertIn("object", tb._serialize_update(object()))
        bot = SimpleNamespace(leave_chat=AsyncMock())
        self.assertTrue(await tb._leave_chat(db, bot, -1))
        bot.leave_chat.side_effect = BadRequest("leave")
        self.assertFalse(await tb._leave_chat(db, bot, -1))
        self.assertEqual(tb._parse_chat_id("-10"), -10)
        self.assertEqual(tb._parse_chat_id("@channel"), "@channel")
        self.assertEqual(tb._chat_language(db, None), "es")
        self.assertEqual(tb._chat_language(db, -1), "es")
        self.assertTrue(tb._is_bot_removed_error(Forbidden("x")))
        self.assertFalse(tb._is_bot_removed_error(TelegramError("x")))
        self.assertTrue(tb._is_bot_removed_error(BadRequest("chat not found")))
        self.assertFalse(tb._is_bot_removed_error(BadRequest("other")))
        naive = message_stub(date=datetime(2026, 7, 22, 3))
        self.assertIsNotNone(tb._telegram_message_datetime(naive).tzinfo)
        self.assertEqual(tb._galeraza_game_date(naive), "2026-07-22")


class HisopoTelegramTests(unittest.IsolatedAsyncioTestCase):
    def _spawn(self, **overrides) -> HisopoSpawn:
        values = dict(
            chat_id="-1",
            message_id="100",
            hisopo_type="common",
            appearance_type="common",
            points=1,
            source="message",
            spawned_at="2099-08-20T12:00:00+00:00",
            expires_at="2099-08-20T12:20:00+00:00",
            status="active",
            winner_user_id=None,
            captured_at=None,
        )
        values.update(overrides)
        return HisopoSpawn(**values)

    def _application(self, db=None, **setting_overrides):
        bot_state = state(db or MagicMock(), **setting_overrides)
        bot = SimpleNamespace(
            send_photo=AsyncMock(return_value=SimpleNamespace(message_id=100)),
            delete_messages=AsyncMock(return_value=True),
            edit_message_caption=AsyncMock(),
            edit_message_media=AsyncMock(),
            get_chat_member_count=AsyncMock(return_value=16),
        )
        job_queue = MagicMock()
        application = SimpleNamespace(
            bot_data={"state": bot_state},
            bot=bot,
            job_queue=job_queue,
            process_error=AsyncMock(return_value=False),
        )
        return application, bot_state, bot, job_queue

    async def test_old_hisopo_cleanup_filters_batches_and_records_outcomes(self) -> None:
        now = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
        db = MagicMock()
        db.list_pending_hisopo_message_cleanups.return_value = [
            HisopoMessageCleanup("-1", "1", "2026-08-19T13:00:00", 0, None),
            HisopoMessageCleanup("-1", "2", "2026-08-19T11:00:00+00:00", 0, None),
            HisopoMessageCleanup(
                "-1", "3", "2026-08-19T10:00:00+00:00", 1,
                "2026-08-20T11:55:00+00:00",
            ),
            HisopoMessageCleanup(
                "-1", "4", "2026-08-19T09:00:00+00:00", 1,
                "2026-08-20T11:49:00",
            ),
            HisopoMessageCleanup("-1", "5", "2026-08-18T11:00:00+00:00", 0, None),
        ]
        application, _, bot, _ = self._application(db)

        with self.assertLogs(tb.logger, level="INFO") as logs:
            await tb._cleanup_old_hisopo_messages(application, "-1", now)

        bot.delete_messages.assert_awaited_once_with(
            chat_id=-1,
            message_ids=[2, 4],
            read_timeout=5,
            write_timeout=5,
            connect_timeout=5,
            pool_timeout=5,
        )
        db.mark_hisopo_messages_deleted.assert_called_once_with(
            "-1", ["2", "4"], now
        )
        db.mark_hisopo_messages_cleanup_expired.assert_called_once_with(
            "-1",
            ["5"],
            now,
            "Telegram no permite borrar mensajes enviados hace 48 horas o mas.",
        )
        self.assertTrue(any("Descarte de la cola interna" in line for line in logs.output))
        self.assertTrue(any("Borre 2 mensaje" in line for line in logs.output))

    async def test_cleanup_failure_is_logged_retried_and_never_blocks_spawn(self) -> None:
        now = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
        cleanup = HisopoMessageCleanup(
            "-1", "90", "2026-08-19T11:00:00+00:00", 0, None
        )
        db = MagicMock()
        db.list_pending_hisopo_message_cleanups.return_value = [cleanup]
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        db.save_hisopo_spawn.return_value = self._spawn()
        application, _, bot, _ = self._application(
            db,
            telegram_hisopo_common_file_id="common-id",
        )
        bot.delete_messages.side_effect = TimedOut()

        with self.assertLogs(tb.logger, level="WARNING") as logs, patch.object(
            tb.secrets, "randbelow", return_value=0
        ):
            result = await tb._spawn_hisopo(application, "-1", "message", now=now)

        self.assertEqual(result, self._spawn())
        bot.send_photo.assert_awaited_once()
        db.record_hisopo_message_cleanup_failure.assert_called_once_with(
            "-1", ["90"], now, "Timed out", 3
        )
        self.assertTrue(any("se enviara igualmente" in line for line in logs.output))

        bot.delete_messages.side_effect = None
        bot.delete_messages.return_value = False
        db.record_hisopo_message_cleanup_failure.reset_mock()
        with self.assertLogs(tb.logger, level="WARNING"):
            await tb._cleanup_old_hisopo_messages(application, "-1", now)
        db.record_hisopo_message_cleanup_failure.assert_called_once()

        db.list_pending_hisopo_message_cleanups.side_effect = RuntimeError("db unavailable")
        bot.send_photo.reset_mock()
        with self.assertLogs(tb.logger, level="WARNING") as unexpected_logs, patch.object(
            tb.secrets, "randbelow", return_value=0
        ):
            await tb._spawn_hisopo(application, "-1", "message", now=now)
        bot.send_photo.assert_awaited_once()
        self.assertTrue(any("envio igualmente" in line for line in unexpected_logs.output))

    async def test_message_spawn_gates_and_spawn_delivery(self) -> None:
        db = MagicMock()
        application, bot_state, bot, job_queue = self._application(
            db,
            telegram_hisopo_common_file_id="common-id",
        )
        private = message_stub(chat=SimpleNamespace(id=1, type="private", title=None))
        self.assertIsNone(await tb._maybe_spawn_hisopo_for_message(application, private))

        group = message_stub()
        db.is_command_group_enabled.return_value = False
        self.assertIsNone(await tb._maybe_spawn_hisopo_for_message(application, group))
        db.is_command_group_enabled.return_value = True
        db.get_hisopo_intensity_percent.return_value = 10
        with patch.object(tb.secrets, "randbelow", return_value=99):
            self.assertIsNone(await tb._maybe_spawn_hisopo_for_message(application, group))

        spawn = self._spawn()
        db.save_hisopo_spawn.return_value = spawn
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        with patch.object(tb.secrets, "randbelow", side_effect=[0, 0]):
            self.assertEqual(await tb._maybe_spawn_hisopo_for_message(application, group), spawn)
        bot.send_photo.assert_awaited_once()
        self.assertEqual(bot.send_photo.await_args.kwargs["photo"], "common-id")
        self.assertEqual(bot.send_photo.await_args.kwargs["reply_markup"].inline_keyboard[0][0].callback_data, "hisopo:capture")
        job_queue.run_once.assert_called_once()

        with patch.object(tb.secrets, "randbelow", return_value=0):
            missing_application, _, _, _ = self._application(db)
            with self.assertRaisesRegex(tb.HisopoSpawnError, "file_id comun"):
                await tb._spawn_hisopo(missing_application, "-1", "message")
        bot.send_photo.side_effect = TimedOut()
        with patch.object(tb.secrets, "randbelow", return_value=0):
            with self.assertRaisesRegex(tb.HisopoSpawnError, "chat_id=-1") as raised:
                await tb._spawn_hisopo(application, "-1", "message")
        self.assertIsInstance(raised.exception.__cause__, TimedOut)

        update = SimpleNamespace(update_id=5)
        with patch.object(tb.secrets, "randbelow", side_effect=[0, 0]):
            self.assertIsNone(
                await tb._maybe_spawn_hisopo_for_message(application, group, update)
            )
        application.process_error.assert_awaited_once()
        self.assertIs(application.process_error.await_args.kwargs["update"], update)
        self.assertIsInstance(
            application.process_error.await_args.kwargs["error"],
            tb.HisopoSpawnError,
        )

        bot.send_photo.side_effect = None
        db.save_hisopo_spawn.return_value = spawn
        with patch.object(tb.secrets, "randbelow", return_value=0):
            await tb._spawn_hisopo(
                application,
                "-1",
                "message",
                now=datetime(2026, 8, 20, 12),
            )
        self.assertEqual(db.save_hisopo_spawn.call_args.kwargs["spawned_at"], "2026-08-20T12:00:00+00:00")

    async def test_special_spawn_values_expiration_and_missing_file_fallback(self) -> None:
        db = MagicMock()
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        db.save_hisopo_spawn.side_effect = lambda **values: self._spawn(
            **{
                key: value
                for key, value in values.items()
                if key
                in {
                    "chat_id",
                    "message_id",
                    "hisopo_type",
                    "appearance_type",
                    "points",
                    "source",
                    "spawned_at",
                    "expires_at",
                    "required_helpers",
                    "bomb_success_slot",
                    "bomb_explosion_slot",
                }
            }
        )

        fallback_app, _, fallback_bot, _ = self._application(
            db,
            telegram_hisopo_common_file_id="common-id",
        )
        with patch.object(tb.secrets, "randbelow", side_effect=[9365, 0]):
            fallback_spawn = await tb._spawn_hisopo(fallback_app, "-1", "message")
        self.assertEqual(fallback_spawn.hisopo_type, "common")
        self.assertEqual(fallback_bot.send_photo.await_args.kwargs["photo"], "common-id")

        mystery_app, _, mystery_bot, _ = self._application(
            db,
            telegram_hisopo_common_file_id="common-id",
            telegram_hisopo_mystery_file_id="mystery-id",
        )
        with patch.object(tb.secrets, "randbelow", side_effect=[6565, 0]):
            mystery_spawn = await tb._spawn_hisopo(
                mystery_app,
                "-1",
                "message",
                now=datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
            )
        self.assertEqual(mystery_spawn.hisopo_type, "common")
        self.assertEqual(mystery_spawn.appearance_type, "mystery")
        self.assertEqual(mystery_spawn.points, 1)
        self.assertEqual(mystery_spawn.expires_at, "2026-08-20T12:20:00+00:00")
        self.assertEqual(
            mystery_bot.send_photo.await_args.kwargs["caption"],
            "¡Apareció un nuevo hisopo!\nhisopo misterioso · valor oculto",
        )

        mystery_fleeting_app, _, _, _ = self._application(
            db,
            telegram_hisopo_mystery_file_id="mystery-id",
            telegram_hisopo_fleeting_file_id="fleeting-id",
        )
        with patch.object(tb.secrets, "randbelow", side_effect=[6565, 5865]):
            mystery_fleeting = await tb._spawn_hisopo(
                mystery_fleeting_app,
                "-1",
                "message",
                now=datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
            )
        self.assertEqual(mystery_fleeting.hisopo_type, "fleeting")
        self.assertEqual(mystery_fleeting.appearance_type, "mystery")
        self.assertEqual(mystery_fleeting.expires_at, "2026-08-20T12:20:00+00:00")

        fake_app, _, fake_bot, _ = self._application(
            db,
            telegram_hisopo_common_file_id="common-id",
            telegram_hisopo_fake_file_id="fake-id",
        )
        with patch.object(tb.secrets, "randbelow", side_effect=[9365, 0]):
            fake_spawn = await tb._spawn_hisopo(fake_app, "-1", "message")
        self.assertEqual(fake_spawn.hisopo_type, "fake")
        self.assertEqual(fake_spawn.appearance_type, "common")
        self.assertEqual(
            fake_bot.send_photo.await_args.kwargs["caption"],
            "¡Apareció un nuevo hisopo!\nhisopo común · 1 pt",
        )

        putrid_app, _, putrid_bot, _ = self._application(
            db,
            telegram_hisopo_diamond_file_id="diamond-id",
            telegram_hisopo_putrid_file_id="putrid-id",
        )
        with patch.object(tb.secrets, "randbelow", side_effect=[7265, 99]):
            putrid_spawn = await tb._spawn_hisopo(putrid_app, "-1", "message")
        self.assertEqual(putrid_spawn.hisopo_type, "putrid")
        self.assertEqual(putrid_spawn.appearance_type, "diamond")
        self.assertEqual(
            putrid_bot.send_photo.await_args.kwargs["caption"],
            "¡Apareció un nuevo hisopo!\nhisopo diamante · 10 pt",
        )

        radioactive_app, _, radioactive_bot, _ = self._application(
            db,
            telegram_hisopo_radioactive_file_id="radioactive-id",
        )
        with patch.object(tb.secrets, "randbelow", return_value=7765):
            radioactive_spawn = await tb._spawn_hisopo(
                radioactive_app,
                "-1",
                "message",
            )
        self.assertEqual(radioactive_spawn.points, 0)
        self.assertEqual(
            radioactive_bot.send_photo.await_args.kwargs["caption"],
            "¡Apareció un nuevo hisopo!\nhisopo radiactivo · valor oculto",
        )

        bomb_app, _, bomb_bot, _ = self._application(
            db,
            telegram_hisopo_bomb_file_id="bomb-id",
            telegram_hisopo_bomb_defused_file_id="bomb-defused-id",
            telegram_hisopo_bomb_exploded_file_id="bomb-exploded-id",
        )
        with patch.object(tb.secrets, "randbelow", side_effect=[8165, 2, 6]):
            bomb_spawn = await tb._spawn_hisopo(bomb_app, "-1", "message")
        self.assertEqual(bomb_spawn.hisopo_type, "bomb")
        self.assertEqual(bomb_spawn.bomb_success_slot, 2)
        self.assertEqual(bomb_spawn.bomb_explosion_slot, 7)
        self.assertEqual(
            bomb_bot.send_photo.await_args.kwargs["caption"],
            "¡Apareció un Hisopo bomba!\nElegí una casilla: una lo desactiva, "
            "otra lo hace explotar y las demás no hacen nada.",
        )
        bomb_keyboard = bomb_bot.send_photo.await_args.kwargs["reply_markup"].inline_keyboard
        self.assertEqual(len(bomb_keyboard), 4)
        self.assertTrue(all(len(row) == 4 for row in bomb_keyboard))
        self.assertEqual(bomb_keyboard[0][0].text, "❓")
        self.assertEqual(bomb_keyboard[3][3].callback_data, "hisopo:bomb:15")

        frenetic_app, _, frenetic_bot, _ = self._application(
            db,
            telegram_hisopo_frenetic_file_id="frenetic-id",
        )
        with patch.object(tb.secrets, "randbelow", return_value=8565):
            frenetic_spawn = await tb._spawn_hisopo(frenetic_app, "-1", "message")
        self.assertEqual(frenetic_spawn.hisopo_type, "frenetic")
        self.assertEqual(
            frenetic_bot.send_photo.await_args.kwargs["caption"],
            "¡Apareció un hisopo frenético!\n"
            "La primera persona que llegue a 20 pulsaciones gana.",
        )
        race_button = frenetic_bot.send_photo.await_args.kwargs[
            "reply_markup"
        ].inline_keyboard[0][0]
        self.assertEqual(race_button.text, "Pulsar")
        self.assertEqual(race_button.callback_data, "hisopo:race")

        black_hole_app, _, black_hole_bot, _ = self._application(
            db,
            telegram_hisopo_black_hole_file_id="black-hole-id",
        )
        with patch.object(tb.secrets, "randbelow", return_value=8965):
            black_hole_spawn = await tb._spawn_hisopo(
                black_hole_app,
                "-1",
                "message",
            )
        self.assertEqual(black_hole_spawn.hisopo_type, "black_hole")
        self.assertEqual(
            black_hole_bot.send_photo.await_args.kwargs["photo"],
            "black-hole-id",
        )

        fleeting_app, _, _, _ = self._application(
            db,
            telegram_hisopo_common_file_id="common-id",
            telegram_hisopo_fleeting_file_id="fleeting-id",
        )
        with patch.object(tb.secrets, "randbelow", return_value=5865):
            fleeting_spawn = await tb._spawn_hisopo(
                fleeting_app,
                "-1",
                "message",
                now=datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
            )
        self.assertEqual(fleeting_spawn.hisopo_type, "fleeting")
        self.assertEqual(fleeting_spawn.expires_at, "2026-08-20T12:01:00+00:00")

        giant_app, _, giant_bot, _ = self._application(
            db,
            telegram_hisopo_giant_file_id="giant-id",
        )
        giant_bot.get_chat_member_count.return_value = 12
        with patch.object(tb.secrets, "randbelow", return_value=9965):
            giant_spawn = await tb._spawn_hisopo(giant_app, "-1", "message")
        self.assertEqual(giant_spawn.hisopo_type, "giant")
        self.assertEqual(giant_spawn.required_helpers, 11)
        self.assertEqual(
            giant_bot.send_photo.await_args.kwargs["caption"],
            "¡Apareció un Hisopo gigante cooperativo!\n"
            "Progreso: 0/11 · Premio: 4 pt por participante",
        )
        self.assertEqual(
            giant_bot.send_photo.await_args.kwargs["reply_markup"].inline_keyboard[0][0].text,
            "Ayudar a capturarlo (0/11)",
        )
        giant_bot.get_chat_member_count.side_effect = BadRequest("members")
        with self.assertLogs(tb.logger, level="WARNING"), patch.object(
            tb.secrets,
            "randbelow",
            return_value=9965,
        ):
            fallback_giant = await tb._spawn_hisopo(giant_app, "-1", "message")
        self.assertEqual(fallback_giant.required_helpers, 15)

        miracle_app, _, miracle_bot, _ = self._application(
            db,
            telegram_hisopo_miracle_file_id="miracle-id",
        )
        with patch.object(tb.secrets, "randbelow", return_value=9990):
            miracle_spawn = await tb._spawn_hisopo(miracle_app, "-1", "message")
        self.assertEqual(miracle_spawn.hisopo_type, "miracle")
        self.assertEqual(miracle_spawn.points, 15)
        self.assertIn("valor oculto", miracle_bot.send_photo.await_args.kwargs["caption"])

    def test_file_ids_restore_scheduling_and_seconds(self) -> None:
        app, bot_state, _bot, job_queue = self._application(
            telegram_hisopo_common_file_id="c",
            telegram_hisopo_silver_file_id="s",
            telegram_hisopo_gold_file_id="g",
            telegram_hisopo_diamond_file_id="d",
            telegram_hisopo_fleeting_file_id="fl",
            telegram_hisopo_mystery_file_id="m",
            telegram_hisopo_putrid_file_id="p",
            telegram_hisopo_used_file_id="u",
            telegram_hisopo_radioactive_file_id="r",
            telegram_hisopo_bomb_file_id="b",
            telegram_hisopo_bomb_defused_file_id="bd",
            telegram_hisopo_bomb_exploded_file_id="be",
            telegram_hisopo_frenetic_file_id="fr",
            telegram_hisopo_black_hole_file_id="bh",
            telegram_hisopo_expired_file_id="ex",
            telegram_hisopo_fake_file_id="f",
            telegram_hisopo_twin_file_id="t",
            telegram_hisopo_giant_file_id="gi",
            telegram_hisopo_miracle_file_id="mi",
        )
        expected_ids = {
            "common": "c",
            "silver": "s",
            "gold": "g",
            "diamond": "d",
            "fleeting": "fl",
            "mystery": "m",
            "putrid": "p",
            "used": "u",
            "radioactive": "r",
            "bomb": "b",
            "frenetic": "fr",
            "black_hole": "bh",
            "expired": "ex",
            "fake": "f",
            "twin": "t",
            "giant": "gi",
            "miracle": "mi",
        }
        for kind, file_id in expected_ids.items():
            self.assertEqual(tb._hisopo_file_id(bot_state.settings, kind), file_id)
        self.assertIsNone(tb._hisopo_file_id(bot_state.settings, "unknown"))

        spawn = self._spawn(expires_at="2999-01-01T00:00:00")
        schedule = HisopoSchedule(1, "-1", "2000-01-01T00:00:00+00:00", "pending", "100")
        bot_state.db.list_active_hisopo_spawns.return_value = [spawn]
        bot_state.db.list_pending_hisopo_schedules.return_value = [schedule]
        tb._restore_hisopo_jobs(app)
        bot_state.db.reset_processing_hisopo_schedules.assert_called_once()
        self.assertEqual(job_queue.run_once.call_count, 2)
        self.assertGreater(tb._seconds_until("2999-01-01T00:00:00"), 0)
        self.assertEqual(tb._seconds_until("2000-01-01T00:00:00+00:00"), 0)

    async def test_expiration_and_scheduled_jobs(self) -> None:
        db = MagicMock()
        app, bot_state, bot, _job_queue = self._application(db)
        context = SimpleNamespace(
            application=app,
            bot=bot,
            job=SimpleNamespace(data={"chat_id": "-1", "message_id": "100"}),
        )
        db.resolve_chat_id.return_value = "-1"
        db.mark_hisopo_expired_waiting.return_value = False
        await tb._expire_hisopo_job(context)
        bot.edit_message_caption.assert_not_awaited()
        db.mark_hisopo_expired_waiting.return_value = True
        await tb._expire_hisopo_job(context)
        self.assertEqual(db.mark_hisopo_expired_waiting.call_count, 2)
        bot.edit_message_caption.assert_not_awaited()

        context.job.data = {"schedule_id": 1}
        db.claim_hisopo_schedule.return_value = None
        await tb._scheduled_hisopo_job(context)
        schedule = HisopoSchedule(1, "-1", "2026-08-21T10:00:00+00:00", "processing", "100")
        db.claim_hisopo_schedule.return_value = schedule
        db.is_command_group_enabled.return_value = False
        await tb._scheduled_hisopo_job(context)
        db.complete_hisopo_schedule.assert_called_with(1, "cancelled")
        db.is_command_group_enabled.return_value = True
        with patch.object(tb, "_spawn_hisopo", AsyncMock(return_value=self._spawn())):
            await tb._scheduled_hisopo_job(context)
        db.complete_hisopo_schedule.assert_called_with(1, "sent")
        with patch.object(tb, "_spawn_hisopo", AsyncMock(return_value=None)):
            await tb._scheduled_hisopo_job(context)
        db.complete_hisopo_schedule.assert_called_with(1, "failed")
        with patch.object(
            tb,
            "_spawn_hisopo",
            AsyncMock(side_effect=tb.HisopoSpawnError("failed spawn")),
        ), self.assertRaisesRegex(tb.HisopoSpawnError, "failed spawn"):
            await tb._scheduled_hisopo_job(context)
        db.complete_hisopo_schedule.assert_called_with(1, "failed")

    async def test_capture_callback_all_outcomes_and_guards(self) -> None:
        db = MagicMock()
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        db.is_user_blocked.return_value = False
        app, bot_state, bot, job_queue = self._application(db)
        message = SimpleNamespace(chat=SimpleNamespace(id=-1, type="group"), message_id=100)
        callback = SimpleNamespace(
            message=message,
            data="hisopo:capture",
            answer=AsyncMock(),
            from_user=SimpleNamespace(id=2),
        )
        user = SimpleNamespace(id=2, full_name="Winner", username="winner")
        update = SimpleNamespace(callback_query=callback, effective_user=user)
        context = SimpleNamespace(application=app, bot=bot)

        await tb._hisopo_callback_entrypoint(
            SimpleNamespace(callback_query=None, effective_user=None), context
        )
        db.is_user_blocked.return_value = True
        await tb._hisopo_callback_entrypoint(update, context)
        callback.answer.assert_awaited_once_with()
        callback.answer.reset_mock()
        db.is_user_blocked.return_value = False

        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=True):
            await tb._hisopo_callback_entrypoint(update, context)
        callback.answer.assert_awaited_once_with()
        callback.answer.reset_mock()

        callback.data = "hisopo:unknown"
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False):
            await tb._hisopo_callback_entrypoint(update, context)
        callback.answer.assert_awaited_once_with("Este hisopo ya no está disponible.", show_alert=True)
        callback.answer.reset_mock()
        callback.data = "hisopo:capture"

        spawn = self._spawn(status="captured", winner_user_id="2", captured_at="now")
        db.get_hisopo_spawn.return_value = spawn
        schedule = HisopoSchedule(1, "-1", "2026-08-21T10:00:00+00:00", "pending", "100")
        db.capture_hisopo.return_value = HisopoCaptureResult("captured", spawn, schedule)
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False), patch.object(
            tb, "random_next_day_datetime", return_value=datetime(2026, 8, 21, tzinfo=timezone.utc)
        ):
            await tb._hisopo_callback_entrypoint(update, context)
        bot.edit_message_caption.assert_awaited_once_with(
            chat_id=-1,
            message_id=100,
            caption="Winner capturó un hisopo común y sumó 1 pt.",
            reply_markup=None,
        )
        job_queue.run_once.assert_called_once()
        callback.answer.assert_awaited_once_with("¡Hisopo capturado! Sumaste 1 pt.")

        for status_name, expected in (
            ("taken", "Uh, qué mala suerte, se te adelantaron."),
            ("missing", "Este hisopo ya no está disponible."),
        ):
            callback.answer.reset_mock()
            db.get_hisopo_spawn.return_value = spawn if status_name == "taken" else None
            db.capture_hisopo.return_value = HisopoCaptureResult(status_name, spawn if status_name == "taken" else None)
            with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False):
                await tb._hisopo_callback_entrypoint(update, context)
            callback.answer.assert_awaited_once_with(expected, show_alert=True)

        callback.answer.reset_mock()
        db.capture_hisopo.return_value = HisopoCaptureResult(
            "rotten",
            self._spawn(
                hisopo_type="fleeting",
                appearance_type="mystery",
                points=5,
                status="rotten",
            ),
        )
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False):
            await tb._hisopo_callback_entrypoint(update, context)
        callback.answer.assert_awaited_once_with(
            "Uh, se pudrió el hisopo. Ya no suma puntos.", show_alert=True
        )
        self.assertEqual(
            bot.edit_message_caption.await_args.kwargs["caption"],
            "Este hisopo misterioso se pudrió. Ya no se puede capturar.",
        )
        callback.answer.reset_mock()
        db.capture_hisopo.return_value = HisopoCaptureResult("rotten", None)
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False):
            await tb._hisopo_callback_entrypoint(update, context)
        callback.answer.assert_awaited_once()

    async def test_capture_callback_negative_zero_and_twin_effects(self) -> None:
        db = MagicMock()
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        db.is_user_blocked.return_value = False
        app, _, bot, job_queue = self._application(
            db,
            telegram_hisopo_fake_file_id="fake-id",
            telegram_hisopo_putrid_file_id="putrid-id",
        )
        message = SimpleNamespace(chat=SimpleNamespace(id=-1, type="group"), message_id=100)
        callback = SimpleNamespace(
            message=message,
            data="hisopo:capture",
            answer=AsyncMock(),
            from_user=SimpleNamespace(id=2),
        )
        user = SimpleNamespace(id=2, full_name="Winner", username="winner")
        update = SimpleNamespace(callback_query=callback, effective_user=user)
        context = SimpleNamespace(application=app, bot=bot)

        active_putrid = self._spawn(
            hisopo_type="putrid",
            appearance_type="gold",
            points=-2,
        )
        captured_putrid = self._spawn(
            hisopo_type="putrid",
            appearance_type="gold",
            points=-2,
            status="captured",
            winner_user_id="2",
            captured_at="now",
        )
        db.get_hisopo_spawn.return_value = active_putrid
        db.capture_hisopo.return_value = HisopoCaptureResult("captured", captured_putrid)
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False):
            await tb._hisopo_callback_entrypoint(update, context)
        self.assertEqual(
            bot.edit_message_media.await_args.kwargs["media"].caption,
            "Winner capturó un hisopo putrefacto y perdió 2 pt.",
        )
        self.assertEqual(bot.edit_message_media.await_args.kwargs["media"].media, "putrid-id")
        callback.answer.assert_awaited_once_with("¡Hisopo capturado! Perdiste 2 pt.")
        job_queue.run_once.assert_not_called()

        bot.edit_message_caption.reset_mock()
        callback.answer.reset_mock()
        active_fake = self._spawn(
            hisopo_type="fake",
            appearance_type="common",
            points=0,
        )
        captured_fake = self._spawn(
            hisopo_type="fake",
            appearance_type="common",
            points=0,
            status="captured",
            winner_user_id="2",
            captured_at="now",
        )
        db.get_hisopo_spawn.return_value = active_fake
        db.capture_hisopo.return_value = HisopoCaptureResult("captured", captured_fake)
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False):
            await tb._hisopo_callback_entrypoint(update, context)
        self.assertEqual(
            db.capture_hisopo.call_args.kwargs["next_scheduled_for"],
            (),
        )
        self.assertEqual(
            bot.edit_message_media.await_args.kwargs["media"].caption,
            "Winner iba a capturar un hisopo, ¡pero resultó ser falso! No suma ningún punto.",
        )
        self.assertEqual(bot.edit_message_media.await_args.kwargs["media"].media, "fake-id")
        callback.answer.assert_awaited_once_with("Este hisopo no valía puntos.")

        bot.edit_message_caption.reset_mock()
        bot.edit_message_media.reset_mock()
        callback.answer.reset_mock()
        active_zero = self._spawn(points=0)
        captured_zero = self._spawn(
            points=0,
            status="captured",
            winner_user_id="2",
            captured_at="now",
        )
        db.get_hisopo_spawn.return_value = active_zero
        db.capture_hisopo.return_value = HisopoCaptureResult("captured", captured_zero)
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False):
            await tb._hisopo_callback_entrypoint(update, context)
        self.assertEqual(
            bot.edit_message_caption.await_args.kwargs["caption"],
            "Winner capturó un hisopo común, pero no sumó ningún punto.",
        )
        callback.answer.assert_awaited_once_with("Este hisopo no valía puntos.")

        bot.edit_message_caption.reset_mock()
        bot.edit_message_media.reset_mock()
        callback.answer.reset_mock()
        active_twin = self._spawn(hisopo_type="twin", points=4)
        captured_twin = self._spawn(
            hisopo_type="twin",
            points=4,
            status="captured",
            winner_user_id="2",
            captured_at="now",
        )
        db.get_hisopo_spawn.return_value = active_twin
        db.capture_hisopo.return_value = HisopoCaptureResult(
            "captured",
            captured_twin,
        )
        with patch.object(
            tb, "_is_user_restricted_in_callback_chat", return_value=False
        ), patch.object(
            tb,
            "random_next_day_datetime",
            return_value=datetime(2026, 8, 21, 1, tzinfo=timezone.utc),
        ), patch.object(tb, "_spawn_hisopo", AsyncMock()) as immediate_spawn:
            await tb._hisopo_callback_entrypoint(update, context)
        self.assertEqual(job_queue.run_once.call_count, 0)
        immediate_spawn.assert_awaited_once_with(app, "-1", source="twin")
        callback.answer.assert_awaited_once_with("¡Hisopo capturado! Sumaste 4 pt.")

    async def test_bomb_callbacks_reveal_persist_and_close_atomically(self) -> None:
        db = MagicMock()
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        db.is_user_blocked.return_value = False
        app, _, bot, job_queue = self._application(
            db,
            telegram_hisopo_bomb_file_id="bomb-id",
            telegram_hisopo_bomb_defused_file_id="bomb-defused-id",
            telegram_hisopo_bomb_exploded_file_id="bomb-exploded-id",
        )
        message = SimpleNamespace(chat=SimpleNamespace(id=-1, type="group"), message_id=100)
        user = SimpleNamespace(id=2, full_name="Winner", username="winner")
        callback = SimpleNamespace(
            message=message,
            data="hisopo:capture",
            answer=AsyncMock(),
            from_user=user,
        )
        update = SimpleNamespace(callback_query=callback, effective_user=user)
        context = SimpleNamespace(application=app, bot=bot)
        mystery = self._spawn(
            hisopo_type="bomb",
            appearance_type="mystery",
            initial_appearance_type="mystery",
            points=10,
            bomb_success_slot=2,
            bomb_explosion_slot=7,
        )
        revealed = replace(mystery, appearance_type="bomb")
        db.get_hisopo_spawn.return_value = mystery
        db.reveal_bomb_hisopo.return_value = HisopoBombResult("revealed", revealed)
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False):
            await tb._hisopo_callback_entrypoint(update, context)
        self.assertEqual(bot.edit_message_media.await_args.kwargs["media"].media, "bomb-id")
        self.assertEqual(len(bot.edit_message_media.await_args.kwargs["reply_markup"].inline_keyboard), 4)
        callback.answer.assert_awaited_once_with(
            "¡Era un Hisopo bomba! Ahora elegí una casilla.",
            show_alert=True,
        )

        callback.answer.reset_mock()
        bot.edit_message_media.reset_mock()
        callback.data = "hisopo:bomb:0"
        active = replace(revealed, bomb_revealed_mask=0)
        missed = replace(revealed, bomb_revealed_mask=1)
        db.get_hisopo_spawn.return_value = active
        db.resolve_bomb_hisopo_slot.return_value = HisopoBombResult("miss", missed)
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False), patch.object(
            tb,
            "random_next_day_datetime",
            return_value=datetime(2026, 8, 21, 10, tzinfo=timezone.utc),
        ):
            await tb._hisopo_callback_entrypoint(update, context)
        keyboard = bot.edit_message_caption.await_args.kwargs["reply_markup"].inline_keyboard
        self.assertEqual(keyboard[0][0].text, "➖")
        self.assertEqual(keyboard[0][0].callback_data, "hisopo:bomb:used")
        callback.answer.assert_awaited_once_with("No desactivaste la bomba.", show_alert=True)

        callback.answer.reset_mock()
        callback.data = "hisopo:bomb:used"
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False):
            await tb._hisopo_callback_entrypoint(update, context)
        callback.answer.assert_awaited_once_with()

        callback.answer.reset_mock()
        callback.data = "hisopo:bomb:2"
        schedule = HisopoSchedule(1, "-1", "2026-08-21T10:00:00+00:00", "pending", "100")
        defused = replace(
            active,
            status="captured",
            points=10,
            winner_user_id="2",
            captured_at="2026-08-20T12:00:00+00:00",
        )
        db.resolve_bomb_hisopo_slot.return_value = HisopoBombResult(
            "captured", defused, schedule
        )
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False), patch.object(
            tb,
            "random_next_day_datetime",
            return_value=datetime(2026, 8, 21, 10, tzinfo=timezone.utc),
        ):
            await tb._hisopo_callback_entrypoint(update, context)
        self.assertEqual(
            bot.edit_message_media.await_args.kwargs["media"].media,
            "bomb-defused-id",
        )
        self.assertEqual(
            bot.edit_message_media.await_args.kwargs["media"].caption,
            "Winner desactivó el Hisopo bomba y ganó 10 pt.",
        )
        self.assertIsNone(bot.edit_message_media.await_args.kwargs["reply_markup"])
        callback.answer.assert_awaited_once_with(
            "¡Desactivaste la bomba! Ganaste 10 pt.", show_alert=True
        )
        job_queue.run_once.assert_called_once()

        callback.answer.reset_mock()
        callback.data = "hisopo:bomb:7"
        exploded = replace(
            active,
            status="exploded",
            points=-10,
            winner_user_id="2",
            captured_at="2026-08-20T12:00:00+00:00",
        )
        db.resolve_bomb_hisopo_slot.return_value = HisopoBombResult(
            "exploded", exploded
        )
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False):
            await tb._hisopo_callback_entrypoint(update, context)
        self.assertEqual(
            bot.edit_message_media.await_args.kwargs["media"].media,
            "bomb-exploded-id",
        )
        self.assertEqual(
            bot.edit_message_media.await_args.kwargs["media"].caption,
            "¡El Hisopo bomba le explotó a Winner! Perdió 10 pt.",
        )
        callback.answer.assert_awaited_once_with(
            "¡Explotó la bomba! Perdiste 10 pt.", show_alert=True
        )

        for status in ("already_revealed", "taken"):
            callback.answer.reset_mock()
            db.resolve_bomb_hisopo_slot.return_value = HisopoBombResult(status, active)
            with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False):
                await tb._hisopo_callback_entrypoint(update, context)
            callback.answer.assert_awaited_once_with()

        self.assertIsNone(tb._parse_bomb_slot("hisopo:bomb:used"))
        self.assertIsNone(tb._parse_bomb_slot("hisopo:bomb:16"))
        self.assertEqual(tb._parse_bomb_slot("hisopo:bomb:15"), 15)

    async def test_bomb_stale_rotten_and_edit_failure_paths(self) -> None:
        db = MagicMock()
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        db.is_user_blocked.return_value = False
        app, bot_state, bot, _ = self._application(
            db,
            telegram_hisopo_bomb_file_id="bomb-id",
            telegram_hisopo_bomb_defused_file_id="bomb-defused-id",
            telegram_hisopo_bomb_exploded_file_id="bomb-exploded-id",
        )
        user = SimpleNamespace(id=2, full_name="Winner", username="winner")
        message = SimpleNamespace(chat=SimpleNamespace(id=-1, type="group"), message_id=100)
        callback = SimpleNamespace(
            message=message,
            data="hisopo:bomb:0",
            answer=AsyncMock(),
            from_user=user,
        )
        context = SimpleNamespace(application=app, bot=bot)
        update = SimpleNamespace(callback_query=callback, effective_user=user)
        db.get_hisopo_spawn.return_value = None
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False):
            await tb._hisopo_callback_entrypoint(update, context)
        callback.answer.assert_awaited_once_with()
        callback.answer.reset_mock()
        db.get_hisopo_spawn.return_value = self._spawn()
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False):
            await tb._hisopo_callback_entrypoint(update, context)
        callback.answer.assert_awaited_once_with()

        active = self._spawn(
            hisopo_type="bomb",
            appearance_type="bomb",
            points=10,
            bomb_success_slot=2,
            bomb_explosion_slot=7,
        )
        mystery = replace(active, appearance_type="mystery")
        rotten = replace(active, status="rotten")
        callback.answer.reset_mock()
        for status in ("already_revealed", "taken"):
            db.reveal_bomb_hisopo.return_value = HisopoBombResult(status, active)
            await tb._handle_bomb_hisopo_reveal(
                context,
                callback,
                user,
                mystery,
                "es",
                datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
            )
        self.assertEqual(callback.answer.await_count, 2)

        callback.answer.reset_mock()
        db.reveal_bomb_hisopo.return_value = HisopoBombResult("rotten", rotten)
        await tb._handle_bomb_hisopo_reveal(
            context, callback, user, mystery, "es", datetime.now(timezone.utc)
        )
        callback.answer.assert_awaited_once_with(
            "Uh, se pudrió el hisopo. Ya no suma puntos.", show_alert=True
        )
        callback.answer.reset_mock()
        db.reveal_bomb_hisopo.return_value = HisopoBombResult("rotten", None)
        await tb._handle_bomb_hisopo_reveal(
            context, callback, user, mystery, "es", datetime.now(timezone.utc)
        )
        callback.answer.assert_awaited_once_with(
            "Uh, se pudrió el hisopo. Ya no suma puntos.", show_alert=True
        )
        callback.answer.reset_mock()
        db.reveal_bomb_hisopo.return_value = HisopoBombResult("invalid", active)
        await tb._handle_bomb_hisopo_reveal(
            context, callback, user, mystery, "es", datetime.now(timezone.utc)
        )
        callback.answer.assert_awaited_once_with(
            "Este hisopo ya no está disponible.", show_alert=True
        )

        callback.answer.reset_mock()
        db.resolve_bomb_hisopo_slot.return_value = HisopoBombResult("rotten", rotten)
        await tb._handle_bomb_hisopo_slot(
            context, callback, user, active, 0, "es", datetime.now(timezone.utc)
        )
        callback.answer.assert_awaited_once_with(
            "Uh, se pudrió el hisopo. Ya no suma puntos.", show_alert=True
        )
        callback.answer.reset_mock()
        db.resolve_bomb_hisopo_slot.return_value = HisopoBombResult("rotten", None)
        await tb._handle_bomb_hisopo_slot(
            context, callback, user, active, 0, "es", datetime.now(timezone.utc)
        )
        callback.answer.assert_awaited_once_with(
            "Uh, se pudrió el hisopo. Ya no suma puntos.", show_alert=True
        )
        callback.answer.reset_mock()
        db.resolve_bomb_hisopo_slot.return_value = HisopoBombResult("invalid", active)
        await tb._handle_bomb_hisopo_slot(
            context, callback, user, active, 0, "es", datetime.now(timezone.utc)
        )
        callback.answer.assert_awaited_once_with(
            "Este hisopo ya no está disponible.", show_alert=True
        )

        callback.answer.reset_mock()
        defused = replace(active, status="captured", winner_user_id="2", captured_at="now")
        db.resolve_bomb_hisopo_slot.return_value = HisopoBombResult("captured", defused)
        await tb._handle_bomb_hisopo_slot(
            context, callback, user, active, 2, "es", datetime.now(timezone.utc)
        )
        callback.answer.assert_awaited_once()

        fallback_settings = settings()
        fallback_bot = SimpleNamespace(
            edit_message_media=AsyncMock(),
            edit_message_caption=AsyncMock(),
        )
        await tb._edit_bomb_hisopo_board(
            fallback_bot,
            fallback_settings,
            active,
            "board",
            force_media=True,
        )
        fallback_bot.edit_message_media.assert_not_awaited()
        fallback_bot.edit_message_caption.assert_awaited_once()

        fallback_bot.edit_message_caption.reset_mock()
        fallback_bot.edit_message_media.side_effect = BadRequest("media")
        with self.assertLogs(tb.logger, level="WARNING"):
            await tb._edit_bomb_hisopo_board(
                fallback_bot,
                bot_state.settings,
                active,
                "board",
                force_media=True,
            )
        fallback_bot.edit_message_caption.assert_awaited_once()

        fallback_bot.edit_message_media.side_effect = None
        fallback_bot.edit_message_caption.reset_mock(side_effect=True)
        fallback_bot.edit_message_caption.side_effect = BadRequest("caption")
        with self.assertLogs(tb.logger, level="WARNING"):
            await tb._edit_bomb_hisopo_board(
                fallback_bot,
                fallback_settings,
                active,
                "board",
            )

        fallback_bot.edit_message_caption.side_effect = None
        fallback_bot.edit_message_caption.reset_mock()
        await tb._edit_bomb_hisopo_terminal(
            fallback_bot,
            fallback_settings,
            defused,
            None,
            "done",
        )
        fallback_bot.edit_message_caption.assert_awaited_once()

        fallback_bot.edit_message_caption.reset_mock()
        fallback_bot.edit_message_media.side_effect = BadRequest("media")
        with self.assertLogs(tb.logger, level="WARNING"):
            await tb._edit_bomb_hisopo_terminal(
                fallback_bot,
                bot_state.settings,
                defused,
                "bomb-defused-id",
                "done",
            )
        fallback_bot.edit_message_caption.assert_awaited_once()

    async def test_race_callbacks_keep_progress_private_finish_and_report_stale_states(self) -> None:
        db = MagicMock()
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        app, _, bot, job_queue = self._application(
            db,
            telegram_hisopo_frenetic_file_id="frenetic-id",
            telegram_hisopo_black_hole_file_id="black-hole-id",
        )
        callback = SimpleNamespace(id="callback-1", answer=AsyncMock())
        context = SimpleNamespace(application=app, bot=bot)
        user = SimpleNamespace(id=2, full_name="Winner", username="winner")
        active = self._spawn(
            hisopo_type="frenetic",
            appearance_type="frenetic",
            points=3,
        )

        db.press_hisopo_race.return_value = HisopoRaceResult(
            "pressed",
            active,
            user_press_count=7,
            participant_count=2,
        )
        await tb._handle_hisopo_race_callback(
            context, callback, user, active, "es", datetime.now(timezone.utc)
        )
        bot.edit_message_caption.assert_not_awaited()
        bot.edit_message_media.assert_not_awaited()
        callback.answer.assert_awaited_once_with("Tu pulsación contó: 7/20.")

        bot.edit_message_caption.reset_mock()
        callback.answer.reset_mock()
        db.press_hisopo_race.return_value = HisopoRaceResult(
            "pressed", active, user_press_count=8
        )
        await tb._handle_hisopo_race_callback(
            context, callback, user, active, "es", datetime.now(timezone.utc)
        )
        bot.edit_message_caption.assert_not_awaited()
        callback.answer.assert_awaited_once_with("Tu pulsación contó: 8/20.")

        callback.answer.reset_mock()
        revealed_race = replace(active, appearance_type="frenetic")
        db.press_hisopo_race.return_value = HisopoRaceResult(
            "pressed",
            revealed_race,
            user_press_count=1,
            participant_count=1,
            revealed=True,
        )
        await tb._handle_hisopo_race_callback(
            context, callback, user, active, "es", datetime.now(timezone.utc)
        )
        self.assertEqual(
            bot.edit_message_media.await_args.kwargs["media"].caption,
            "¡Apareció un hisopo frenético!\n"
            "La primera persona que llegue a 20 pulsaciones gana.",
        )
        self.assertEqual(
            bot.edit_message_media.await_args.kwargs[
                "reply_markup"
            ].inline_keyboard[0][0].text,
            "Pulsar",
        )
        callback.answer.assert_awaited_once_with("Tu pulsación contó: 1/20.")

        callback.answer.reset_mock()
        db.press_hisopo_race.return_value = HisopoRaceResult("too_fast", active)
        await tb._handle_hisopo_race_callback(
            context, callback, user, active, "es", datetime.now(timezone.utc)
        )
        callback.answer.assert_awaited_once_with(
            "Esa pulsación fue demasiado rápida y no contó."
        )

        callback.answer.reset_mock()
        db.press_hisopo_race.return_value = HisopoRaceResult("duplicate", active)
        await tb._handle_hisopo_race_callback(
            context, callback, user, active, "es", datetime.now(timezone.utc)
        )
        callback.answer.assert_awaited_once_with()

        callback.answer.reset_mock()
        schedule = HisopoSchedule(
            1, "-1", "2099-08-21T10:00:00+00:00", "pending", "100"
        )
        won = replace(
            active,
            status="captured",
            winner_user_id="2",
            captured_at="2099-08-20T12:01:00+00:00",
        )
        db.press_hisopo_race.return_value = HisopoRaceResult(
            "captured",
            won,
            user_press_count=20,
            participant_count=2,
            awarded_points=3,
            schedule=schedule,
        )
        await tb._handle_hisopo_race_callback(
            context, callback, user, active, "es", datetime.now(timezone.utc)
        )
        self.assertEqual(
            bot.edit_message_caption.await_args.kwargs["caption"],
            "Winner ganó la carrera por el hisopo frenético y sumó 3 pt.",
        )
        job_queue.run_once.assert_called_once()
        callback.answer.assert_awaited_once_with(
            "¡Ganaste la carrera! Sumaste 3 pt.", show_alert=True
        )

        black = replace(
            active,
            hisopo_type="black_hole",
            appearance_type="black_hole",
            points=10,
        )
        for participants, awarded, losses, expected_caption in (
            (
                1,
                10,
                (),
                "Winner dominó en soledad el hisopo agujero negro y sumó 10 pt.",
            ),
            (
                3,
                5,
                (("3", 3), ("4", 2)),
                "Winner dominó el hisopo agujero negro: ganó 5 pt y absorbió "
                "5 pt de 2 rival(es).",
            ),
        ):
            bot.edit_message_caption.reset_mock()
            callback.answer.reset_mock()
            db.press_hisopo_race.return_value = HisopoRaceResult(
                "captured",
                replace(black, status="captured", points=awarded),
                user_press_count=20,
                participant_count=participants,
                awarded_points=awarded,
                lost_points_by_user=losses,
            )
            await tb._handle_hisopo_race_callback(
                context, callback, user, black, "es", datetime.now(timezone.utc)
            )
            self.assertEqual(
                bot.edit_message_caption.await_args.kwargs["caption"],
                expected_caption,
            )

        for status, expected in (
            ("taken", "Uh, qué mala suerte, se te adelantaron."),
            ("missing", "Este hisopo ya no está disponible."),
        ):
            callback.answer.reset_mock()
            db.press_hisopo_race.return_value = HisopoRaceResult(status, active)
            await tb._handle_hisopo_race_callback(
                context, callback, user, active, "es", datetime.now(timezone.utc)
            )
            callback.answer.assert_awaited_once_with(expected, show_alert=True)

        callback.answer.reset_mock()
        expired = replace(active, status="expired", appearance_type="expired")
        db.press_hisopo_race.return_value = HisopoRaceResult("rotten", active)
        db.claim_expired_hisopo.return_value = HisopoExpirationResult(
            "expired", expired, True
        )
        with patch.object(tb, "_edit_expired_hisopo", AsyncMock()) as edit_expired:
            await tb._handle_hisopo_race_callback(
                context, callback, user, active, "es", datetime.now(timezone.utc)
            )
        edit_expired.assert_awaited_once()
        callback.answer.assert_awaited_once_with(
            "Era un hisopo frenético, pero se te venció, así que lo perdiste.",
            show_alert=True,
        )

        callback.answer.reset_mock()
        db.press_hisopo_race.return_value = HisopoRaceResult("rotten", active)
        db.claim_expired_hisopo.return_value = HisopoExpirationResult(
            "taken", active, False
        )
        with patch.object(tb, "_edit_expired_hisopo", AsyncMock()) as edit_expired:
            await tb._handle_hisopo_race_callback(
                context, callback, user, active, "es", datetime.now(timezone.utc)
            )
        edit_expired.assert_not_awaited()
        callback.answer.assert_awaited_once_with(
            "Era un hisopo frenético, pero se te venció, así que lo perdiste.",
            show_alert=True,
        )

    async def test_expired_callback_changes_media_and_mystery_only_reveals(self) -> None:
        db = MagicMock()
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        db.is_user_blocked.return_value = False
        app, _, bot, _ = self._application(
            db,
            telegram_hisopo_expired_file_id="expired-id",
            telegram_hisopo_gold_file_id="gold-id",
        )
        message = SimpleNamespace(chat=SimpleNamespace(id=-1, type="group"), message_id=100)
        user = SimpleNamespace(id=2, full_name="Late", username="late")
        callback = SimpleNamespace(
            id="late-1",
            message=message,
            data="hisopo:capture",
            answer=AsyncMock(),
            from_user=user,
        )
        update = SimpleNamespace(callback_query=callback, effective_user=user)
        context = SimpleNamespace(application=app, bot=bot)
        past = self._spawn(
            expires_at="2020-01-01T00:00:00+00:00",
            status="expired_waiting",
        )
        db.get_hisopo_spawn.return_value = past
        db.claim_expired_hisopo.return_value = HisopoExpirationResult(
            "expired",
            replace(past, status="expired", appearance_type="expired"),
            True,
        )
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False):
            await tb._hisopo_callback_entrypoint(update, context)
        self.assertEqual(bot.edit_message_media.await_args.kwargs["media"].media, "expired-id")
        self.assertEqual(
            bot.edit_message_media.await_args.kwargs["media"].caption,
            "Era un hisopo común, pero se te venció, así que lo perdiste.",
        )
        callback.answer.assert_awaited_once_with(
            "Era un hisopo común, pero se te venció, así que lo perdiste.",
            show_alert=True,
        )

        bot.edit_message_media.reset_mock()
        callback.answer.reset_mock()
        mystery = replace(
            past,
            hisopo_type="gold",
            points=3,
            appearance_type="mystery",
            initial_appearance_type="mystery",
        )
        db.get_hisopo_spawn.return_value = mystery
        db.claim_expired_hisopo.return_value = HisopoExpirationResult(
            "expired",
            replace(mystery, status="expired", appearance_type="gold"),
            False,
        )
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False):
            await tb._hisopo_callback_entrypoint(update, context)
        self.assertEqual(bot.edit_message_media.await_args.kwargs["media"].media, "gold-id")
        self.assertEqual(
            "Era un hisopo dorado, pero se te venció, así que lo perdiste.",
            bot.edit_message_media.await_args.kwargs["media"].caption,
        )
        callback.answer.assert_awaited_once_with(
            "Era un hisopo dorado, pero se te venció, así que lo perdiste.",
            show_alert=True,
        )

        callback.answer.reset_mock()
        db.claim_expired_hisopo.return_value = HisopoExpirationResult("taken", mystery)
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False):
            await tb._hisopo_callback_entrypoint(update, context)
        callback.answer.assert_awaited_once_with(
            "Este hisopo ya no está disponible.", show_alert=True
        )

        callback.answer.reset_mock()
        callback.data = "hisopo:race"
        active_race = self._spawn(
            hisopo_type="frenetic",
            appearance_type="frenetic",
        )
        db.get_hisopo_spawn.return_value = active_race
        with patch.object(
            tb, "_is_user_restricted_in_callback_chat", return_value=False
        ), patch.object(
            tb, "_handle_hisopo_race_callback", AsyncMock()
        ) as handle_race:
            await tb._hisopo_callback_entrypoint(update, context)
        handle_race.assert_awaited_once()

        callback.data = "hisopo:bomb:0"
        waiting_bomb = self._spawn(
            hisopo_type="bomb",
            appearance_type="bomb",
            points=10,
            status="expired_waiting",
            bomb_success_slot=2,
            bomb_explosion_slot=7,
        )
        db.get_hisopo_spawn.return_value = waiting_bomb
        db.claim_expired_hisopo.return_value = HisopoExpirationResult(
            "active", waiting_bomb
        )
        with patch.object(
            tb, "_is_user_restricted_in_callback_chat", return_value=False
        ), patch.object(
            tb, "_handle_bomb_hisopo_slot", AsyncMock()
        ) as handle_bomb:
            await tb._hisopo_callback_entrypoint(update, context)
        handle_bomb.assert_awaited_once()

    async def test_race_reveal_and_expired_edit_fallbacks_are_non_fatal(self) -> None:
        active = self._spawn(hisopo_type="frenetic", appearance_type="frenetic")
        fallback_bot = SimpleNamespace(
            edit_message_media=AsyncMock(side_effect=BadRequest("media")),
            edit_message_caption=AsyncMock(),
        )
        configured = settings(
            telegram_hisopo_frenetic_file_id="frenetic-id",
            telegram_hisopo_expired_file_id="expired-id",
        )
        success_bot = SimpleNamespace(
            edit_message_media=AsyncMock(),
            edit_message_caption=AsyncMock(),
        )
        await tb._reveal_hisopo_race(success_bot, configured, active, "es")
        success_bot.edit_message_media.assert_awaited_once()
        success_bot.edit_message_caption.assert_not_awaited()

        with self.assertLogs(tb.logger, level="WARNING"):
            await tb._reveal_hisopo_race(fallback_bot, configured, active, "es")
        fallback_bot.edit_message_caption.assert_awaited_once()

        fallback_bot.edit_message_caption.reset_mock()
        with self.assertLogs(tb.logger, level="WARNING"):
            await tb._reveal_hisopo_race(fallback_bot, settings(), active, "es")
        fallback_bot.edit_message_caption.assert_awaited_once()

        fallback_bot.edit_message_caption.reset_mock()
        expired = replace(active, status="expired", appearance_type="expired")
        with self.assertLogs(tb.logger, level="WARNING"):
            await tb._edit_expired_hisopo(
                fallback_bot, configured, expired, "es", True
            )
        fallback_bot.edit_message_caption.assert_awaited_once()

        fallback_bot.edit_message_caption.reset_mock()
        with self.assertLogs(tb.logger, level="WARNING"):
            await tb._edit_expired_hisopo(
                fallback_bot, settings(), expired, "es", True
            )
        fallback_bot.edit_message_caption.assert_awaited_once()

        fallback_bot.edit_message_caption.side_effect = BadRequest("caption")
        with self.assertLogs(tb.logger, level="WARNING"):
            await tb._reveal_hisopo_race(fallback_bot, settings(), active, "es")

    async def test_giant_callback_reveals_progress_prevents_duplicates_and_completes(self) -> None:
        db = MagicMock()
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        app, _, bot, job_queue = self._application(
            db,
            telegram_hisopo_giant_file_id="giant-id",
        )
        callback = SimpleNamespace(answer=AsyncMock())
        context = SimpleNamespace(application=app, bot=bot)
        user = SimpleNamespace(id=2, full_name="Helper", username="helper")
        active = self._spawn(
            hisopo_type="giant",
            appearance_type="mystery",
            points=4,
            required_helpers=2,
        )
        revealed = self._spawn(
            hisopo_type="giant",
            appearance_type="giant",
            points=4,
            required_helpers=2,
        )
        scheduled = HisopoSchedule(
            1,
            "-1",
            "2026-08-21T10:00:00+00:00",
            "pending",
            "100",
        )
        db.contribute_to_giant_hisopo.return_value = HisopoGiantContributionResult(
            "joined",
            revealed,
            ("2",),
            1,
            2,
            revealed=True,
        )
        with patch.object(
            tb,
            "random_next_day_datetime",
            return_value=datetime(2026, 8, 21, 10, tzinfo=timezone.utc),
        ):
            await tb._handle_giant_hisopo_callback(
                context,
                callback,
                user,
                active,
                "es",
                datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
            )
        self.assertEqual(bot.edit_message_media.await_args.kwargs["media"].media, "giant-id")
        self.assertIn("Progreso: 1/2", bot.edit_message_media.await_args.kwargs["media"].caption)
        callback.answer.assert_awaited_once_with("¡Ayudaste! Van 1/2.")

        bot.edit_message_media.reset_mock()
        callback.answer.reset_mock()
        db.contribute_to_giant_hisopo.return_value = HisopoGiantContributionResult(
            "already_joined",
            revealed,
            ("2",),
            1,
            2,
        )
        await tb._handle_giant_hisopo_callback(
            context,
            callback,
            user,
            revealed,
            "es",
            datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
        )
        callback.answer.assert_awaited_once_with(
            "Ya ayudaste con este Hisopo. Van 1/2.",
            show_alert=True,
        )
        bot.edit_message_media.assert_not_awaited()

        callback.answer.reset_mock()
        db.contribute_to_giant_hisopo.return_value = HisopoGiantContributionResult(
            "completed",
            replace(revealed, status="captured", winner_user_id="2"),
            ("2", "3"),
            2,
            2,
            scheduled,
            True,
        )
        await tb._handle_giant_hisopo_callback(
            context,
            callback,
            user,
            active,
            "es",
            datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
        )
        media = bot.edit_message_media.await_args.kwargs["media"]
        self.assertEqual(media.media, "giant-id")
        self.assertEqual(
            media.caption,
            "¡Hisopo gigante capturado! Cooperaron 2 personas y cada una ganó 4 pt.",
        )
        self.assertIsNone(bot.edit_message_media.await_args.kwargs["reply_markup"])
        callback.answer.assert_awaited_once_with("¡Lo lograron! Ganaste 4 pt.")
        job_queue.run_once.assert_called_once()

    async def test_giant_entrypoint_and_remaining_callback_outcomes(self) -> None:
        db = MagicMock()
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        db.is_user_blocked.return_value = False
        db.get_giant_contribution_count.return_value = 1
        app, _, bot, job_queue = self._application(
            db,
            telegram_hisopo_giant_file_id="giant-id",
        )
        active = self._spawn(
            hisopo_type="giant",
            appearance_type="giant",
            points=4,
            required_helpers=2,
        )
        message = SimpleNamespace(chat=SimpleNamespace(id=-1, type="group"), message_id=100)
        user = SimpleNamespace(id=2, full_name="Helper", username="helper")
        callback = SimpleNamespace(
            message=message,
            data="hisopo:capture",
            answer=AsyncMock(),
            from_user=user,
        )
        context = SimpleNamespace(application=app, bot=bot)
        db.get_hisopo_spawn.return_value = active
        db.contribute_to_giant_hisopo.return_value = HisopoGiantContributionResult(
            "taken",
            replace(active, status="captured"),
        )
        with patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False):
            await tb._hisopo_callback_entrypoint(
                SimpleNamespace(callback_query=callback, effective_user=user),
                context,
            )
        callback.answer.assert_awaited_once_with(
            "Uh, qué mala suerte, se te adelantaron.",
            show_alert=True,
        )

        callback.answer.reset_mock()
        db.contribute_to_giant_hisopo.return_value = HisopoGiantContributionResult(
            "completed",
            replace(active, status="captured", winner_user_id="2"),
            ("2", "3"),
            2,
            2,
        )
        await tb._handle_giant_hisopo_callback(
            context,
            callback,
            user,
            active,
            "es",
            datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
        )
        job_queue.run_once.assert_not_called()
        callback.answer.assert_awaited_once_with("¡Lo lograron! Ganaste 4 pt.")

        callback.answer.reset_mock()
        db.contribute_to_giant_hisopo.return_value = HisopoGiantContributionResult(
            "rotten",
            replace(active, status="rotten"),
        )
        await tb._handle_giant_hisopo_callback(
            context,
            callback,
            user,
            active,
            "es",
            datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
        )
        self.assertEqual(
            bot.edit_message_caption.await_args.kwargs["caption"],
            "El Hisopo gigante se pudrió con 1/2 ayudas. No se entregaron puntos.",
        )
        callback.answer.assert_awaited_once_with(
            "Uh, se pudrió el hisopo. Ya no suma puntos.",
            show_alert=True,
        )

        callback.answer.reset_mock()
        db.contribute_to_giant_hisopo.return_value = HisopoGiantContributionResult(
            "rotten",
            None,
        )
        await tb._handle_giant_hisopo_callback(
            context,
            callback,
            user,
            active,
            "es",
            datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
        )
        callback.answer.assert_awaited_once_with(
            "Uh, se pudrió el hisopo. Ya no suma puntos.",
            show_alert=True,
        )

        callback.answer.reset_mock()
        db.contribute_to_giant_hisopo.return_value = HisopoGiantContributionResult(
            "invalid",
            active,
        )
        await tb._handle_giant_hisopo_callback(
            context,
            callback,
            user,
            active,
            "es",
            datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
        )
        callback.answer.assert_awaited_once_with(
            "Este hisopo ya no está disponible.",
            show_alert=True,
        )

    async def test_radioactive_capture_calculates_and_reveals_final_points(self) -> None:
        db = MagicMock()
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        db.is_user_blocked.return_value = False
        app, _, bot, job_queue = self._application(db)
        message = SimpleNamespace(chat=SimpleNamespace(id=-1, type="group"), message_id=100)
        callback = SimpleNamespace(
            message=message,
            data="hisopo:capture",
            answer=AsyncMock(),
            from_user=SimpleNamespace(id=2),
        )
        user = SimpleNamespace(id=2, full_name="Winner", username="winner")
        update = SimpleNamespace(callback_query=callback, effective_user=user)
        context = SimpleNamespace(application=app, bot=bot)
        active = self._spawn(
            hisopo_type="radioactive",
            appearance_type="radioactive",
            points=0,
            spawned_at="2026-08-20T12:00:00+00:00",
        )
        db.get_hisopo_spawn.return_value = active

        def capture(**kwargs):
            return HisopoCaptureResult(
                "captured",
                self._spawn(
                    hisopo_type="radioactive",
                    appearance_type="radioactive",
                    points=kwargs["points_at_capture"],
                    status="captured",
                    winner_user_id="2",
                    captured_at=kwargs["now"].isoformat(),
                ),
                HisopoSchedule(
                    1,
                    "-1",
                    "2026-08-21T01:00:00+00:00",
                    "pending",
                    "100",
                ),
            )

        db.capture_hisopo.side_effect = capture
        captured_at = datetime(2026, 8, 20, 12, 19, tzinfo=timezone.utc)
        with patch.object(tb, "datetime") as datetime_mock, patch.object(
            tb,
            "random_next_day_datetime",
            return_value=datetime(2026, 8, 21, 1, tzinfo=timezone.utc),
        ), patch.object(tb, "_is_user_restricted_in_callback_chat", return_value=False):
            datetime_mock.now.return_value = captured_at
            datetime_mock.fromisoformat.side_effect = datetime.fromisoformat
            await tb._hisopo_callback_entrypoint(update, context)

        self.assertEqual(db.capture_hisopo.call_args.kwargs["points_at_capture"], 6)
        self.assertEqual(
            bot.edit_message_caption.await_args.kwargs["caption"],
            "Winner capturó un hisopo radiactivo y sumó 6 pt.",
        )
        callback.answer.assert_awaited_once_with("¡Hisopo capturado! Sumaste 6 pt.")
        job_queue.run_once.assert_called_once()

    async def test_mystery_fleeting_after_its_minute_reveals_without_reward(self) -> None:
        db = MagicMock()
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        db.is_user_blocked.return_value = False
        app, _, bot, job_queue = self._application(
            db,
            telegram_hisopo_fleeting_file_id="fleeting-id",
        )
        message = SimpleNamespace(chat=SimpleNamespace(id=-1, type="group"), message_id=100)
        callback = SimpleNamespace(
            message=message,
            data="hisopo:capture",
            answer=AsyncMock(),
            from_user=SimpleNamespace(id=2),
        )
        user = SimpleNamespace(id=2, full_name="Winner", username="winner")
        update = SimpleNamespace(callback_query=callback, effective_user=user)
        context = SimpleNamespace(application=app, bot=bot)
        active = self._spawn(
            hisopo_type="fleeting",
            appearance_type="mystery",
            points=5,
            spawned_at="2026-08-20T12:00:00+00:00",
            expires_at="2026-08-20T12:20:00+00:00",
        )
        db.get_hisopo_spawn.return_value = active

        def capture(**kwargs):
            return HisopoCaptureResult(
                "captured",
                self._spawn(
                    hisopo_type="fleeting",
                    appearance_type="mystery",
                    points=kwargs["points_at_capture"],
                    status="captured",
                    winner_user_id="2",
                    captured_at=kwargs["now"].isoformat(),
                ),
            )

        db.capture_hisopo.side_effect = capture
        captured_at = datetime(2026, 8, 20, 12, 2, tzinfo=timezone.utc)
        with patch.object(tb, "datetime") as datetime_mock, patch.object(
            tb,
            "random_next_day_datetime",
            return_value=datetime(2026, 8, 21, 1, tzinfo=timezone.utc),
        ) as next_day, patch.object(
            tb,
            "_is_user_restricted_in_callback_chat",
            return_value=False,
        ):
            datetime_mock.now.return_value = captured_at
            datetime_mock.fromisoformat.side_effect = datetime.fromisoformat
            await tb._hisopo_callback_entrypoint(update, context)

        next_day.assert_not_called()
        self.assertEqual(db.capture_hisopo.call_args.kwargs["points_at_capture"], 0)
        self.assertEqual(db.capture_hisopo.call_args.kwargs["next_scheduled_for"], ())
        media = bot.edit_message_media.await_args.kwargs["media"]
        self.assertEqual(media.media, "fleeting-id")
        self.assertEqual(
            media.caption,
            "Winner encontró un hisopo fugaz, pero ya había pasado su minuto fugaz. "
            "No sumó puntos.",
        )
        callback.answer.assert_awaited_once_with(
            "Había un hisopo fugaz, pero se pasó su minuto. No sumaste puntos."
        )
        job_queue.run_once.assert_not_called()

    async def test_caption_edit_failure_is_contained(self) -> None:
        bot = SimpleNamespace(edit_message_caption=AsyncMock(side_effect=BadRequest("edit")))
        with self.assertLogs(tb.logger, level="WARNING"):
            await tb._edit_hisopo_caption(bot, self._spawn(), "caption")

        app, bot_state, reveal_bot, _ = self._application(
            telegram_hisopo_fake_file_id="fake-id",
            telegram_hisopo_giant_file_id="giant-id",
        )
        reveal_bot.edit_message_media.side_effect = BadRequest("media")
        disguised = self._spawn(hisopo_type="fake", appearance_type="common", points=0)
        with self.assertLogs(tb.logger, level="WARNING"):
            await tb._edit_hisopo_result(
                reveal_bot,
                bot_state.settings,
                disguised,
                "caption",
            )
        reveal_bot.edit_message_caption.assert_awaited_once()

        reveal_bot.edit_message_media.reset_mock()
        reveal_bot.edit_message_caption.reset_mock()
        reveal_bot.edit_message_media.side_effect = BadRequest("giant media")
        with self.assertLogs(tb.logger, level="WARNING"):
            await tb._edit_giant_hisopo_progress(
                reveal_bot,
                bot_state.settings,
                self._spawn(
                    hisopo_type="giant",
                    appearance_type="giant",
                    points=4,
                    required_helpers=2,
                ),
                "es",
                1,
                2,
                True,
            )
        reveal_bot.edit_message_caption.assert_awaited_once()

        reveal_bot.edit_message_caption.reset_mock()
        reveal_bot.edit_message_caption.side_effect = BadRequest("giant caption")
        with self.assertLogs(tb.logger, level="WARNING"):
            await tb._edit_giant_hisopo_progress(
                reveal_bot,
                bot_state.settings,
                self._spawn(
                    hisopo_type="giant",
                    appearance_type="giant",
                    points=4,
                    required_helpers=2,
                ),
                "es",
                1,
                2,
                False,
            )

        _, missing_state, missing_bot, _ = self._application()
        await tb._edit_giant_hisopo_progress(
            missing_bot,
            missing_state.settings,
            self._spawn(
                hisopo_type="giant",
                appearance_type="giant",
                points=4,
                required_helpers=2,
            ),
            "es",
            1,
            2,
            True,
        )
        missing_bot.edit_message_caption.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
