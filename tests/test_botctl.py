from __future__ import annotations

from contextlib import closing, redirect_stderr, redirect_stdout
import importlib.util
import io
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "deploy" / "gce" / "botctl.py"
SPEC = importlib.util.spec_from_file_location("galerazo_deploy_botctl", SCRIPT)
assert SPEC and SPEC.loader
botctl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(botctl)


def create_database(path: Path) -> None:
    with closing(sqlite3.connect(path)) as connection:
        connection.executescript(
            """
            CREATE TABLE users (user_id TEXT PRIMARY KEY, display_name TEXT, username TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE chats (chat_id TEXT PRIMARY KEY, chat_type TEXT NOT NULL, title TEXT);
            CREATE TABLE chat_command_settings (chat_id TEXT, command_group TEXT, enabled INTEGER, PRIMARY KEY (chat_id, command_group));
            CREATE TABLE blocked_users (user_id TEXT PRIMARY KEY, blocked_by_user_id TEXT NOT NULL, blocked_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE triggers (
                chat_id TEXT NOT NULL,
                trigger_name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                text TEXT,
                media_type TEXT,
                file_id TEXT,
                caption TEXT,
                payload_json TEXT,
                created_by_user_id TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, trigger_name)
            );
            INSERT INTO users (user_id, display_name, username) VALUES ('42', 'Persona real', 'persona');
            INSERT INTO chats (chat_id, chat_type, title) VALUES ('-100', 'supergroup', 'Chat real');
            INSERT INTO triggers (chat_id, trigger_name, display_name, text, media_type, file_id, created_by_user_id)
            VALUES ('-100', 'hola mundo', 'Hola Mundo', 'Respuesta real', 'photo', 'telegram-file-id', '42');
            """
        )


class BotControlContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database = self.root / "galerazo.sqlite3"
        create_database(self.database)
        self.compose = self.root / "compose.yaml"
        self.compose.write_text("services: {}\n", encoding="utf-8")
        self.env = self.root / "bot.env"
        self.env.write_text(
            "TELEGRAM_BOT_TOKEN=123456789:abcdefghijklmnopqrstuvwxyzABCDEF\n"
            "TELEGRAM_LOG_CHAT_ID=-1004440313456\n",
            encoding="utf-8",
        )
        self.constants = patch.multiple(
            botctl,
            DATABASE_PATH=self.database,
            COMPOSE_PATH=self.compose,
            COMPOSE_DIRECTORY=self.root,
            IMAGE_ENV_PATH=self.root / "image.env",
            ENV_PATH=self.env,
        )
        self.constants.start()

    def tearDown(self) -> None:
        self.constants.stop()
        self.temporary.cleanup()

    def test_lists_only_real_database_triggers_with_creator_and_chat(self) -> None:
        with patch.object(botctl, "_file_metadata", return_value=("foto.jpg", "image/jpeg", "photos/foto.jpg")):
            payload = botctl.list_triggers()

        self.assertEqual(len(payload["triggers"]), 1)
        trigger = payload["triggers"][0]
        self.assertEqual(trigger["name"], "Hola Mundo")
        self.assertEqual(trigger["createdBy"]["displayName"], "Persona real")
        self.assertEqual(trigger["chat"]["title"], "Chat real")
        self.assertEqual(trigger["media"]["kind"], "image")
        self.assertEqual(botctl._decode_trigger_id(trigger["id"]), ("-100", "hola mundo"))

    def test_moderation_deletes_blocks_and_attempts_the_warning(self) -> None:
        trigger_id = botctl._encode_trigger_id("-100", "hola mundo")
        with patch.object(botctl, "_telegram_json", return_value={"ok": True, "result": {}}) as telegram:
            result = botctl.moderate_trigger(trigger_id, "delete-and-block")

        self.assertTrue(result["triggerDeleted"])
        self.assertTrue(result["userBlocked"])
        self.assertTrue(result["announcementSent"])
        telegram.assert_called_once()
        with closing(sqlite3.connect(self.database)) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM triggers").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT user_id FROM blocked_users").fetchone()[0], "42")

    def test_status_reports_no_container_and_telegram_connectivity(self) -> None:
        with (
            patch.object(botctl, "_container_id", return_value=None),
            patch.object(botctl, "_telegram_json", return_value={"ok": True, "result": {"username": "GalerazoBot"}}),
        ):
            status = botctl.runtime_status()

        self.assertEqual(status["vm"]["status"], "running")
        self.assertFalse(status["container"]["exists"])
        self.assertTrue(status["telegram"]["connected"])
        self.assertIn("No existe", status["alerts"][0])

    def test_stop_is_nondestructive_compose_stop(self) -> None:
        with patch.object(botctl, "_run") as run:
            result = botctl.stop_service()
        self.assertTrue(result["stopped"])
        command = run.call_args.args[0]
        self.assertEqual(command[-2:], ["stop", "bot"])
        self.assertIn(str(self.root / "image.env"), command)
        self.assertNotIn("down", command)

    def test_release_notifications_are_fixed_and_target_the_log_chat(self) -> None:
        with patch.object(
            botctl, "_telegram_json", return_value={"ok": True, "result": {}}
        ) as telegram:
            result = botctl.notify_release("succeeded")

        self.assertEqual(result, {"notified": True, "event": "succeeded"})
        method, _token, fields = telegram.call_args.args
        self.assertEqual(method, "sendMessage")
        self.assertEqual(fields["chat_id"], "-1004440313456")
        self.assertIn("terminé", fields["text"])

    def test_failed_release_notification_includes_a_bounded_sanitized_detail(self) -> None:
        detail = (
            "Falló con 123456789:abcdefghijklmnopqrstuvwxyzABCDEF\n"
            + "x" * 900
        )
        encoded = botctl.base64.b64encode(detail.encode("utf-8")).decode("ascii")
        with patch.object(
            botctl, "_telegram_json", return_value={"ok": True, "result": {}}
        ) as telegram:
            result = botctl.notify_release("failed", encoded)

        self.assertEqual(result, {"notified": True, "event": "failed"})
        message = telegram.call_args.args[2]["text"]
        self.assertIn("Causa: Falló con [TELEGRAM_TOKEN_OCULTO]", message)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyzABCDEF", message)
        self.assertLessEqual(len(message.split("Causa: ", 1)[1]), 800)

    def test_release_notification_rejects_missing_invalid_or_unexpected_detail(self) -> None:
        with self.assertRaisesRegex(ValueError, "detalle es obligatorio"):
            botctl.notify_release("failed")
        with self.assertRaisesRegex(ValueError, "Base64 UTF-8"):
            botctl.notify_release("failed", "no-es-base64!")
        encoded = botctl.base64.b64encode(b"detalle").decode("ascii")
        with self.assertRaisesRegex(ValueError, "solo se admite"):
            botctl.notify_release("succeeded", encoded)
        control = botctl.base64.b64encode(b"detalle\x00oculto").decode("ascii")
        with self.assertRaisesRegex(ValueError, "caracteres de control"):
            botctl.notify_release("failed", control)

    def test_release_notifications_reject_unknown_events(self) -> None:
        with self.assertRaisesRegex(ValueError, "Evento de release inválido"):
            botctl.notify_release("arbitrary-message")

    def test_invalid_cli_and_identifiers_fail_without_leaking_tokens(self) -> None:
        with self.assertRaises(ValueError):
            botctl._decode_trigger_id("../invalid")
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = botctl.main(["unknown"])
        self.assertEqual(code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("error", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
