from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from galerazo_bot.commands import Command as _Command
from galerazo_bot.command_handlers import backup, blacklist, chats, config, debug, galerazas
from galerazo_bot.command_handlers import gastos, novedad, reportar, restrictions, salir, triggers
from galerazo_bot.database import BlockedUser, ChatRestrictedUser, ChatStatsRow, Expense, Trigger, User
from galerazo_bot.expenses import ExpenseSheetStatus, ExpenseSubmissionResult, ExpenseSyncResult
from galerazo_bot.roles import BackupResult, CommandContext, TriggerModerationResult, TriggerPayload, UserLevel


def make_context(**overrides) -> CommandContext:
    context = CommandContext(
        sender_id="1",
        chat_id="-1",
        chat_type="group",
        user_level=UserLevel.DEV,
        raw_text="/test",
        args="",
        bot_user_id="99",
        sender_display_name="Dev",
    )
    return replace(context, **overrides)


class SmallAsyncHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_backup_paths(self) -> None:
        self.assertIn("configurado", await backup.handle(make_context(), MagicMock()))
        sent = AsyncMock(return_value=BackupResult(Path("db"), 1, 2, True))
        self.assertIsNone(await backup.handle(make_context(create_backup=sent), MagicMock()))
        too_large = AsyncMock(return_value=BackupResult(Path("db"), 4 * 1024**2, 2 * 1024**2, False))
        response = await backup.handle(make_context(create_backup=too_large), MagicMock())
        self.assertIn("4.00 MB", response)
        self.assertIn("2 MB", response)

    async def test_config_paths(self) -> None:
        self.assertIn("grupos", await config.handle(make_context(chat_type="private"), MagicMock()))
        self.assertIn("configurado", await config.handle(make_context(), MagicMock()))
        self.assertIn(
            "mostrar",
            await config.handle(make_context(send_config_menu=AsyncMock(return_value=False)), MagicMock()),
        )
        self.assertIsNone(
            await config.handle(make_context(send_config_menu=AsyncMock(return_value=True)), MagicMock())
        )

    async def test_debug_paths(self) -> None:
        self.assertIn("configurado", await debug.handle(make_context(), MagicMock()))
        self.assertIn(
            "enviar",
            await debug.handle(make_context(send_debug_update=AsyncMock(return_value=False)), MagicMock()),
        )
        self.assertIsNone(
            await debug.handle(make_context(send_debug_update=AsyncMock(return_value=True)), MagicMock())
        )

    async def test_galerazas_paths(self) -> None:
        self.assertIn("grupos", await galerazas.handle(make_context(chat_type="private"), MagicMock()))
        self.assertIn("configurado", await galerazas.handle(make_context(), MagicMock()))
        self.assertIn(
            "mostrar",
            await galerazas.handle(make_context(send_galerazas=AsyncMock(return_value=False)), MagicMock()),
        )
        self.assertIsNone(
            await galerazas.handle(make_context(send_galerazas=AsyncMock(return_value=True)), MagicMock())
        )

    async def test_novedad_paths(self) -> None:
        self.assertIn("Uso", await novedad.handle(make_context(args="  "), MagicMock()))
        self.assertIn("configurado", await novedad.handle(make_context(args="hola"), MagicMock()))
        self.assertIn(
            "enviar",
            await novedad.handle(
                make_context(args="hola", send_announcement=AsyncMock(return_value=False)), MagicMock()
            ),
        )
        sender = AsyncMock(return_value=True)
        self.assertIn("enviada", await novedad.handle(make_context(args=" hola ", send_announcement=sender), MagicMock()))
        sender.assert_awaited_once_with("hola")

    async def test_reportar_paths_and_date_fallback(self) -> None:
        db = MagicMock()
        self.assertIn("Uso", await reportar.handle(make_context(args=""), db))
        self.assertIn("configurado", await reportar.handle(make_context(args="bug"), db))
        db.try_record_daily_report.return_value = False
        self.assertIn(
            "un reporte",
            await reportar.handle(make_context(args="bug", send_report=AsyncMock()), db),
        )
        db.try_record_daily_report.return_value = True
        self.assertIn(
            "enviar",
            await reportar.handle(
                make_context(args="bug", send_report=AsyncMock(return_value=False)), db
            ),
        )
        sender = AsyncMock(return_value=True)
        self.assertIn("enviado", await reportar.handle(make_context(args=" bug ", send_report=sender), db))
        sender.assert_awaited_once_with("bug")
        with patch("galerazo_bot.command_handlers.reportar.ZoneInfo", side_effect=RuntimeError):
            self.assertRegex(reportar._today_key(), r"^\d{4}-\d{2}-\d{2}$")

    async def test_salir_paths(self) -> None:
        db = MagicMock()
        self.assertIn("grupos", await salir.handle(make_context(chat_type="private"), db))
        self.assertIn("respond", await salir.handle(make_context(reply_to_user_id=None), db))
        self.assertIn("respond", await salir.handle(make_context(reply_to_user_id="2"), db))
        self.assertIn(
            "configurado",
            await salir.handle(make_context(reply_to_user_id="99"), db),
        )
        self.assertIn(
            "salir",
            await salir.handle(
                make_context(reply_to_user_id="99", leave_chat=AsyncMock(return_value=False)), db
            ),
        )
        self.assertIn(
            "Saliendo",
            await salir.handle(
                make_context(reply_to_user_id="99", leave_chat=AsyncMock(return_value=True)), db
            ),
        )


class BlacklistAndRestrictionsTests(unittest.TestCase):
    def test_blacklist_all_paths(self) -> None:
        db = MagicMock()
        with patch("galerazo_bot.command_handlers.blacklist.resolve_target_user", return_value=None):
            self.assertIn("respond", blacklist.bloquear(make_context(), db))
            self.assertIn("respond", blacklist.desbloquear(make_context(), db))

        for target, expected in (
            (User("1", "Self", None), "vos mismo"),
            (User("99", "Bot", None), "ocurra"),
            (User(blacklist.GALERAZO_BOT_USER_ID, "Bot", None), "ocurra"),
        ):
            with self.subTest(target=target.user_id), patch(
                "galerazo_bot.command_handlers.blacklist.resolve_target_user", return_value=target
            ):
                self.assertIn(expected, blacklist.bloquear(make_context(), db))

        target = User("2", "Target", "alias")
        with patch("galerazo_bot.command_handlers.blacklist.resolve_target_user", return_value=target):
            self.assertIn("bloqueado", blacklist.bloquear(make_context(), db))
            db.block_user.assert_called_once_with(user_id="2", blocked_by_user_id="1")
            db.unblock_user.return_value = False
            self.assertIn("no estaba", blacklist.desbloquear(make_context(), db))
            db.unblock_user.return_value = True
            self.assertIn("desbloqueado", blacklist.desbloquear(make_context(), db))

        db.list_blocked_users.return_value = []
        self.assertIn("vac", blacklist.listanegra(make_context(), db).lower())
        db.list_blocked_users.return_value = [
            BlockedUser("2", "alias", "Target", "1", "2026-01-01")
        ]
        response = blacklist.listanegra(make_context(), db)
        self.assertIn("Target (2)", response)
        self.assertNotIn("@alias", response)

    def test_restrictions_all_paths(self) -> None:
        db = MagicMock()
        private = make_context(chat_type="private")
        self.assertIn("grupos", restrictions.restringir(private, db))
        self.assertIn("grupos", restrictions.habilitar(private, db))
        self.assertIn("grupos", restrictions.restringidos(private, db))

        with patch("galerazo_bot.command_handlers.restrictions.resolve_target_user", return_value=None):
            self.assertIn("respond", restrictions.restringir(make_context(), db))
            self.assertIn("respond", restrictions.habilitar(make_context(), db))

        target = User("1", "Self", None)
        with patch("galerazo_bot.command_handlers.restrictions.resolve_target_user", return_value=target):
            self.assertIn("vos mismo", restrictions.restringir(make_context(), db))

        target = User("2", "Target", "alias")
        with patch("galerazo_bot.command_handlers.restrictions.resolve_target_user", return_value=target):
            self.assertIn("restringido", restrictions.restringir(make_context(), db))
            db.restrict_user_in_chat.assert_called_once_with(
                chat_id="-1", user_id="2", restricted_by_user_id="1"
            )
            db.unrestrict_user_in_chat.return_value = False
            self.assertIn("no estaba", restrictions.habilitar(make_context(), db))
            db.unrestrict_user_in_chat.return_value = True
            self.assertIn("habilitado", restrictions.habilitar(make_context(), db))

        db.list_restricted_users_in_chat.return_value = []
        self.assertIn("no hay", restrictions.restringidos(make_context(), db).lower())
        db.list_restricted_users_in_chat.return_value = [
            ChatRestrictedUser("-1", "2", "alias", "Target", "1", "2026-01-01")
        ]
        self.assertIn("Target (2)", restrictions.restringidos(make_context(), db))


class ChatAndExpenseHandlerTests(unittest.IsolatedAsyncioTestCase):
    def test_chat_stats_with_present_and_missing_types(self) -> None:
        db = MagicMock()
        db.get_chat_stats.return_value = [ChatStatsRow("group", 2, 1, 1)]
        response = chats.handle(make_context(), db)
        self.assertIn("Total de chats: 2", response)
        self.assertIn("grupos: total 2", response)
        self.assertIn("chats privados: total 0", response)
        self.assertEqual(chats._sum_chat_stats([]), {"total": 0, "active": 0, "inactive": 0})

    def test_enable_and_disable_expenses(self) -> None:
        db = MagicMock()
        private = make_context(chat_type="private")
        self.assertIn("grupos", gastos.habilitargastos(private, db))
        self.assertIn("grupos", gastos.deshabilitargastos(private, db))
        db.is_command_group_enabled.return_value = True
        self.assertIn("habilitados", gastos.habilitargastos(make_context(), db))
        db.is_command_group_enabled.return_value = False
        self.assertIn("habilitados", gastos.habilitargastos(make_context(), db))
        db.set_command_group_enabled.assert_called_with("-1", "gastos", True)
        self.assertIn("deshabilitados", gastos.deshabilitargastos(make_context(), db))
        db.is_command_group_enabled.return_value = True
        self.assertIn("deshabilitados", gastos.deshabilitargastos(make_context(), db))
        db.set_command_group_enabled.assert_called_with("-1", "gastos", False)

    async def test_gasto_all_result_paths(self) -> None:
        db = MagicMock()
        self.assertIn("grupos", await gastos.gasto(make_context(chat_type="private"), db))
        self.assertIn("/gasto", await gastos.gasto(make_context(args="bad"), db))
        valid = "18500 | transferencia | caja | pizzas"
        self.assertIn("configurado", await gastos.gasto(make_context(args=valid), db))
        for result, expected in (
            (ExpenseSubmissionResult(1, True, True), "sincronizado"),
            (ExpenseSubmissionResult(2, False, False), "localmente"),
            (ExpenseSubmissionResult(3, False, True), "pendiente"),
        ):
            sender = AsyncMock(return_value=result)
            response = await gastos.gasto(make_context(args=valid, submit_expense=sender), db)
            self.assertIn(expected, response)
            sender.assert_awaited_once_with("ARS", "1850000", "transferencia", "caja", "pizzas")

    def test_recent_and_status_expenses(self) -> None:
        db = MagicMock()
        private = make_context(chat_type="private")
        self.assertIn("grupos", gastos.ultimosgastos(private, db))
        self.assertIn("grupos", gastos.estadogastos(private, db))
        db.list_recent_expenses.return_value = []
        self.assertIn("hay gastos", gastos.ultimosgastos(make_context(), db))
        db.list_recent_expenses.return_value = [
            Expense(1, "-1", "2", "alias", "User", 12345, "ARS", "cash", "box", "food", "synced", None, "now", "now"),
            Expense(2, "-1", "3", None, None, 100, "ARS", "card", "shop", "item", "pending", None, "now", None),
        ]
        response = gastos.ultimosgastos(make_context(), db)
        self.assertIn("User (2)", response)
        self.assertIn("Usuario (3)", response)
        self.assertIn("sincronizado", response)
        self.assertIn("pendiente", response)

        db.is_command_group_enabled.return_value = False
        db.count_pending_expenses.return_value = 4
        response = gastos.estadogastos(make_context(), db)
        self.assertIn("deshabilitado", response)
        self.assertIn("4", response)
        db.is_command_group_enabled.return_value = True
        status = ExpenseSheetStatus(True, True, True, "Gastos", 2, None)
        response = gastos.estadogastos(make_context(get_expense_sheet_status=lambda: status), db)
        self.assertIn("habilitado", response)
        self.assertIn("2", response)
        status = replace(status, detail="Sheet OK")
        self.assertIn("Sheet OK", gastos.estadogastos(make_context(get_expense_sheet_status=lambda: status), db))

    async def test_sync_expenses_paths(self) -> None:
        db = MagicMock()
        self.assertIn("grupos", await gastos.sincronizargastos(make_context(chat_type="private"), db))
        self.assertIn("configurado", await gastos.sincronizargastos(make_context(), db))
        for result, expected in (
            (ExpenseSyncResult(False, 0, 0), "configurado"),
            (ExpenseSyncResult(True, 2, 0), "Sincronizaci"),
            (ExpenseSyncResult(True, 2, 1), "parcial"),
        ):
            response = await gastos.sincronizargastos(
                make_context(sync_expenses=AsyncMock(return_value=result)), db
            )
            self.assertIn(expected, response)


class TriggerHandlerCompleteTests(unittest.IsolatedAsyncioTestCase):
    async def test_add_validation_and_moderation(self) -> None:
        db = MagicMock()
        self.assertIn("grupos", await triggers.agregartrigger(make_context(chat_type="private"), db))
        self.assertIn("Uso", await triggers.agregartrigger(make_context(args=""), db))
        self.assertIn("entre", await triggers.agregartrigger(make_context(args="x"), db))
        self.assertIn("grupos", await triggers.agregartrigger(make_context(args="valid name", chat_id=None), db))
        self.assertIn("respond", await triggers.agregartrigger(make_context(args="valid name"), db))
        invalid = TriggerPayload()
        self.assertIn(
            "no se puede",
            await triggers.agregartrigger(make_context(args="valid name", reply_to_trigger_payload=invalid), db),
        )
        payload = TriggerPayload(text="answer", data={"dice": "dice"})
        for moderation, expected in (
            (TriggerModerationResult.BLOCKED, "no agregu"),
            (TriggerModerationResult.TOO_LARGE, "límite"),
            (TriggerModerationResult.ERROR, "verificar"),
            (TriggerModerationResult.SKIPPED, "agregado"),
            (TriggerModerationResult.SAFE, "agregado"),
        ):
            db.add_trigger.return_value = True
            response = await triggers.agregartrigger(
                make_context(
                    args=" Valid   Name ",
                    reply_to_trigger_payload=payload,
                    moderate_trigger_payload=AsyncMock(return_value=moderation),
                ),
                db,
            )
            self.assertIn(expected, response.lower())
        kwargs = db.add_trigger.call_args.kwargs
        self.assertEqual(kwargs["trigger_name"], "valid name")
        self.assertIn("dice", kwargs["payload_json"])
        db.add_trigger.return_value = False
        self.assertIn(
            "existe",
            await triggers.agregartrigger(
                make_context(args="valid name", reply_to_trigger_payload=TriggerPayload(text="x")), db
            ),
        )

    def test_delete_list_and_helpers(self) -> None:
        db = MagicMock()
        private = make_context(chat_type="private")
        self.assertIn("grupos", triggers.borrartrigger(private, db))
        self.assertIn("Uso", triggers.borrartrigger(make_context(args=""), db))
        self.assertIn("entre", triggers.borrartrigger(make_context(args="x"), db))
        self.assertIn("grupos", triggers.borrartrigger(make_context(args="valid name", chat_id=None), db))
        db.delete_trigger.return_value = False
        self.assertIn("existe", triggers.borrartrigger(make_context(args="Valid Name"), db))
        db.delete_trigger.return_value = True
        self.assertIn("borrado", triggers.borrartrigger(make_context(args="Valid Name"), db))
        db.delete_trigger.assert_called_with("-1", "valid name")

        self.assertIn("grupos", triggers.triggers(private, db))
        self.assertIn("grupos", triggers.triggers(make_context(chat_id=None), db))
        db.list_triggers.return_value = []
        self.assertIn("hay triggers", triggers.triggers(make_context(), db))
        row = Trigger("-1", "name", "Display Name", "x", None, None, None, "1", "now")
        db.list_triggers.return_value = [row]
        response = triggers.triggers(make_context(), db)
        self.assertTrue(response.startswith("Triggers:\n\n"))
        self.assertIn("- Display Name", response)
        self.assertTrue(triggers._is_valid_payload(TriggerPayload(file_id="f")))
        self.assertFalse(triggers._is_valid_payload(TriggerPayload()))


if __name__ == "__main__":
    unittest.main()
