from __future__ import annotations

import asyncio
import io
import json
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, mock_open, patch


from galerazo_bot import log_checkpoint
from galerazo_bot.instance_lock import SingleInstance
from galerazo_bot.update_processor import PerChatUpdateProcessor


class InstanceLockCompleteTests(unittest.TestCase):
    def test_already_acquired_context_and_empty_release(self) -> None:
        instance = SingleInstance("covered")
        instance._handle = 1
        self.assertTrue(instance.acquire())
        instance._handle = None
        instance._file = object()
        self.assertTrue(instance.acquire())
        instance._file = None
        with patch.object(instance, "acquire", return_value=False):
            with self.assertRaises(RuntimeError):
                instance.__enter__()
        with patch.object(instance, "acquire", return_value=True), patch.object(instance, "release") as release:
            self.assertIs(instance.__enter__(), instance)
            instance.__exit__(None, None, None)
        release.assert_called_once()

    def test_posix_success_blocked_and_release(self) -> None:
        fake_fcntl = SimpleNamespace(LOCK_EX=1, LOCK_NB=2, LOCK_UN=4, flock=MagicMock())
        with tempfile.TemporaryDirectory() as directory, patch.dict(sys.modules, {"fcntl": fake_fcntl}), patch(
            "galerazo_bot.instance_lock.tempfile.gettempdir", return_value=directory
        ):
            instance = SingleInstance("posix-success")
            self.assertTrue(instance._acquire_posix())
            self.assertIsNotNone(instance._file)
            instance._release_posix()
            self.assertIsNone(instance._file)
            instance._release_posix()

            fake_fcntl.flock.side_effect = BlockingIOError
            blocked = SingleInstance("posix-blocked")
            self.assertFalse(blocked._acquire_posix())

    def test_platform_dispatch_and_windows_failure_empty_release(self) -> None:
        instance = SingleInstance("dispatch")
        with patch("galerazo_bot.instance_lock.os.name", "posix"), patch.object(
            instance, "_acquire_posix", return_value=True
        ) as acquire, patch.object(instance, "_release_posix") as release:
            self.assertTrue(instance.acquire())
            instance.release()
        acquire.assert_called_once()
        release.assert_called_once()

        with patch("galerazo_bot.instance_lock.os.name", "nt"), patch.object(
            instance, "_acquire_windows", return_value=True
        ) as acquire, patch.object(instance, "_release_windows") as release:
            self.assertTrue(instance.acquire())
            instance.release()
        acquire.assert_called_once()
        release.assert_called_once()

        instance._handle = None
        instance._release_windows()

        import ctypes

        kernel = MagicMock()
        kernel.CreateMutexW.return_value = 0
        with patch.object(ctypes, "WinDLL", create=True, return_value=kernel), patch.object(
            ctypes, "set_last_error", create=True
        ), patch.object(
            ctypes, "get_last_error", create=True, return_value=5
        ), patch.object(
            ctypes, "WinError", create=True, return_value=OSError("mutex")
        ):
            with self.assertRaisesRegex(OSError, "mutex"):
                SingleInstance("windows-fail")._acquire_windows()

    def test_windows_success_duplicate_and_release(self) -> None:
        import ctypes

        kernel = MagicMock()
        kernel.CreateMutexW.return_value = 42
        with patch.object(ctypes, "WinDLL", create=True, return_value=kernel), patch.object(
            ctypes, "set_last_error", create=True
        ), patch.object(
            ctypes, "get_last_error", create=True, return_value=183
        ):
            duplicate = SingleInstance("windows-duplicate")
            self.assertFalse(duplicate._acquire_windows())
            kernel.CloseHandle.assert_called_once_with(42)

        kernel.reset_mock()
        kernel.CreateMutexW.return_value = 43
        with patch.object(ctypes, "WinDLL", create=True, return_value=kernel), patch.object(
            ctypes, "set_last_error", create=True
        ), patch.object(
            ctypes, "get_last_error", create=True, return_value=0
        ):
            instance = SingleInstance("windows-success")
            self.assertTrue(instance._acquire_windows())
            self.assertEqual(instance._handle, 43)
            instance._release_windows()

        kernel.ReleaseMutex.assert_called_once_with(43)
        kernel.CloseHandle.assert_called_once_with(43)
        self.assertIsNone(instance._handle)


class LogCheckpointCompleteTests(unittest.TestCase):
    def test_missing_rotated_invalid_and_replacement_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / "bot.log"
            checkpoint = root / "checkpoint.json"
            result = log_checkpoint.check_log(log, checkpoint)
            self.assertEqual(result.end_offset, 0)
            log.write_bytes(b"INFO \xff\n")
            checkpoint.write_text(json.dumps({"file_id": "other", "offset": 999}), encoding="utf-8")
            result = log_checkpoint.check_log(log, checkpoint)
            self.assertIn("�", result.new_text)
            checkpoint.write_text("bad", encoding="utf-8")
            self.assertEqual(log_checkpoint._load_checkpoint(checkpoint), {})
            with patch("galerazo_bot.log_checkpoint.json.loads", side_effect=TypeError):
                self.assertEqual(log_checkpoint._load_checkpoint(checkpoint), {})

    def test_main_all_output_paths_and_module_guard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing = root / "missing.log"
            checkpoint = root / "checkpoint.json"
            with patch("sys.argv", ["checkpoint", "--log", str(missing), "--checkpoint", str(checkpoint)]):
                self.assertEqual(log_checkpoint.main(), 0)
            log = root / "bot.log"
            log.write_text("INFO ok\n", encoding="utf-8")
            with patch("sys.argv", ["checkpoint", "--log", str(log), "--checkpoint", str(checkpoint)]):
                self.assertEqual(log_checkpoint.main(), 0)
                self.assertEqual(log_checkpoint.main(), 0)
            log.write_text("INFO ok\nERROR token 123456:abcdefgh\n", encoding="utf-8")
            with patch("sys.argv", ["checkpoint", "--log", str(log), "--checkpoint", str(checkpoint)]):
                self.assertEqual(log_checkpoint.main(), 1)
            with patch(
                "sys.argv",
                ["checkpoint", "--log", str(log), "--checkpoint", str(checkpoint), "--acknowledge"],
            ):
                self.assertEqual(log_checkpoint.main(), 0)
            with patch("sys.argv", ["checkpoint", "--log", str(log), "--checkpoint", str(checkpoint)]):
                self.assertEqual(log_checkpoint.main(), 0)
            with patch(
                "sys.argv",
                ["checkpoint", "--log", str(log), "--checkpoint", str(checkpoint), "--acknowledge"],
            ):
                with self.assertRaises(SystemExit) as exit_result:
                    runpy.run_module("galerazo_bot.log_checkpoint", run_name="__main__")
                self.assertEqual(exit_result.exception.code, 0)


class UpdateProcessorCompleteTests(unittest.IsolatedAsyncioTestCase):
    async def test_lifecycle_chatless_and_same_canonical_migration(self) -> None:
        processor = PerChatUpdateProcessor(lambda chat_id: "canonical" if chat_id == "old" else chat_id)
        await processor.initialize()
        called: list[str] = []

        async def action() -> None:
            called.append("done")

        await processor.do_process_update(object(), action())
        self.assertEqual(called, ["done"])
        processor._aliases["old"] = "canonical"
        migration = MagicMock()
        with patch.object(processor, "_migration_chat_ids", return_value=("old", "canonical")):
            await processor.do_process_update(migration, action())
        self.assertEqual(called, ["done", "done"])
        await processor.shutdown()
        self.assertEqual(processor._aliases, {})
        self.assertEqual(processor._locks, {})

    async def test_alias_resolution_path_compression_and_helpers(self) -> None:
        processor = PerChatUpdateProcessor(lambda chat_id: f"resolved-{chat_id}")
        self.assertEqual(processor._canonical_chat_id("x"), "resolved-x")
        processor._aliases.update({"a": "b", "b": "c", "c": "c"})
        self.assertEqual(processor._canonical_chat_id("a"), "c")
        self.assertEqual(processor._aliases["a"], "c")
        self.assertIs(processor._lock_for("c"), processor._lock_for("c"))
        self.assertIsNone(processor._effective_chat_id(object()))
        self.assertIsNone(processor._migration_chat_ids(object()))

        from datetime import datetime, timezone
        from telegram import Chat, Message, Update, User

        message = Message(1, datetime.now(timezone.utc), Chat(-100, "supergroup"), User(1, "U", False))
        update = Update(1, message=message)
        self.assertEqual(processor._effective_chat_id(update), "-100")
        self.assertIsNone(processor._migration_chat_ids(update))
        migrated_message = Message(
            2,
            datetime.now(timezone.utc),
            Chat(-100, "supergroup"),
            User(1, "U", False),
            migrate_from_chat_id=-1,
        )
        self.assertEqual(
            processor._migration_chat_ids(Update(2, message=migrated_message)),
            ("-1", "-100"),
        )
        update_without_message = Update(2)
        self.assertIsNone(processor._migration_chat_ids(update_without_message))


if __name__ == "__main__":
    unittest.main()
