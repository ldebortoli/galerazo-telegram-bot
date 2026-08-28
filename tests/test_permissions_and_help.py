from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from galerazo_bot.commands import handle_command_async
from galerazo_bot.database import Database
from galerazo_bot.roles import UserLevel


class PermissionsAndHelpTests(unittest.TestCase):
    def test_common_user_cannot_use_dev_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            db.get_or_create_user("1", "Common")

            response = asyncio.run(handle_command_async("/bloquear 2", "1", db))

            self.assertEqual(response, "No tenés permisos suficientes para usar este comando.")
            self.assertFalse(db.is_user_blocked("2"))

    def test_only_developers_can_use_expense_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            db.get_or_create_user("1", "Common")
            db.register_chat("-1", "group", "Group")

            for command in (
                "/gasto ARS 100 | tarjeta | supermercado | compras",
                "/ultimosgastos",
                "/estadogastos",
                "/sincronizargastos",
            ):
                with self.subTest(command=command):
                    response = asyncio.run(
                        handle_command_async(
                            command,
                            "1",
                            db,
                            chat_id="-1",
                            chat_type="group",
                        )
                    )
                    self.assertEqual(response, "No tenés permisos suficientes para usar este comando.")

            response = asyncio.run(
                handle_command_async(
                    "/gasto 100 | tarjeta | supermercado | compras",
                    "1",
                    db,
                    chat_id="1",
                    chat_type="private",
                    user_level=UserLevel.DEV,
                )
            )
            self.assertIn("No hay mecanismo configurado", response)

    def test_bot_cannot_be_blacklisted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            db.get_or_create_user("1", "Developer")

            response = asyncio.run(
                handle_command_async(
                    "/bloquear 573379301",
                    "1",
                    db,
                    user_level=UserLevel.DEV,
                    bot_user_id="573379301",
                )
            )

            self.assertEqual(response, "Ni se te ocurra...")
            self.assertFalse(db.is_user_blocked("573379301"))

    def test_bloqueados_alias_uses_names_without_mentions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            db.get_or_create_user("1", "Developer")
            db.get_or_create_user("2", "Nombre Visible", "alias")
            db.block_user("2", "1")

            response = asyncio.run(
                handle_command_async("/bloqueados", "1", db, user_level=UserLevel.DEV)
            )

            self.assertIn("Nombre Visible (2)", response)
            self.assertNotIn("@alias", response)

    def test_help_is_grouped_and_filtered_by_level(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            db.get_or_create_user("1", "User")

            common_help = asyncio.run(
                handle_command_async("/help", "1", db, chat_id="-1", chat_type="group")
            )
            admin_help = asyncio.run(
                handle_command_async(
                    "/help",
                    "1",
                    db,
                    chat_id="-1",
                    chat_type="group",
                    user_level=UserLevel.ADMIN,
                )
            )
            dev_private_help = asyncio.run(
                handle_command_async(
                    "/help",
                    "1",
                    db,
                    chat_id="1",
                    chat_type="private",
                    user_level=UserLevel.DEV,
                )
            )
            dev_group_help = asyncio.run(
                handle_command_async(
                    "/help",
                    "1",
                    db,
                    chat_id="-1",
                    chat_type="group",
                    user_level=UserLevel.DEV,
                )
            )

            self.assertIn("Comandos generales:", common_help)
            self.assertNotIn("Comandos de desarrollo:", common_help)
            self.assertNotIn("/debug:", common_help)
            self.assertNotIn("enviame /help por privado", common_help)
            self.assertNotIn("enviame /help por privado", admin_help)
            self.assertIn("Comandos de desarrollo:", dev_private_help)
            self.assertIn("/debug:", dev_private_help)
            self.assertIn("/bloquear:", dev_private_help)
            self.assertIn("/salir:", dev_private_help)
            self.assertNotIn("enviame /help por privado", dev_private_help)
            self.assertNotIn("Comandos de desarrollo:", dev_group_help)
            self.assertNotIn("/debug:", dev_group_help)
            self.assertNotIn("/bloquear:", dev_group_help)
            self.assertNotIn("/salir:", dev_group_help)
            self.assertTrue(
                dev_group_help.endswith(
                    "Para ver los comandos de desarrollo, enviame /help por privado."
                )
            )

    def test_expense_help_is_visible_only_to_owner_in_private(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            expense_commands = (
                "/gasto:",
                "/ultimosgastos:",
                "/estadogastos:",
                "/sincronizargastos:",
            )

            owner_private = asyncio.run(
                handle_command_async(
                    "/help",
                    "1",
                    db,
                    chat_id="1",
                    chat_type="private",
                    user_level=UserLevel.DEV,
                    owner_user_id="1",
                )
            )
            owner_group = asyncio.run(
                handle_command_async(
                    "/help",
                    "1",
                    db,
                    chat_id="-1",
                    chat_type="group",
                    user_level=UserLevel.DEV,
                    owner_user_id="1",
                )
            )
            other_dev_private = asyncio.run(
                handle_command_async(
                    "/help",
                    "2",
                    db,
                    chat_id="2",
                    chat_type="private",
                    user_level=UserLevel.DEV,
                    owner_user_id="1",
                )
            )
            unconfigured_owner = asyncio.run(
                handle_command_async(
                    "/help",
                    "1",
                    db,
                    chat_id="1",
                    chat_type="private",
                    user_level=UserLevel.DEV,
                )
            )

            self.assertIn("Comandos de gastos:", owner_private)
            for command in expense_commands:
                with self.subTest(command=command):
                    self.assertIn(command, owner_private)
                    self.assertNotIn(command, owner_group)
                    self.assertNotIn(command, other_dev_private)
                    self.assertNotIn(command, unconfigured_owner)
            self.assertNotIn("Comandos de gastos:", owner_group)
            self.assertNotIn("Comandos de gastos:", other_dev_private)
            self.assertNotIn("Comandos de gastos:", unconfigured_owner)

    def test_help_lists_aliases_and_disabled_configurable_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            db.get_or_create_user("1", "User")
            db.register_chat("-1", "group", "Group")
            self.assertFalse(db.is_command_group_enabled("-1", "ruletarusa"))

            response = asyncio.run(
                handle_command_async(
                    "/help",
                    "1",
                    db,
                    chat_id="-1",
                    chat_type="group",
                )
            )

            for command in (
                "/ayuda:",
                "/agrtrigger:",
                "/eliminartrigger:",
                "/eltrigger:",
                "/coleccionhisopos:",
                "/reglashisopo:",
                "/ruletarusa:",
            ):
                with self.subTest(command=command):
                    self.assertIn(command, response)

            rules = asyncio.run(
                handle_command_async(
                    "/reglashisopo",
                    "1",
                    db,
                    chat_id="-1",
                    chat_type="group",
                )
            )
            self.assertIn("Reglas del Recolector de Hisopos", rules)


if __name__ == "__main__":
    unittest.main()
