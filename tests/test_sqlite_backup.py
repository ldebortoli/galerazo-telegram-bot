from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from deploy.gce.sqlite_backup import BackupConfig, load_config, run_backup


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SqliteBackupRuntimeTests(unittest.TestCase):
    def test_creates_integrity_checked_backup_and_uploads_immutable_objects(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database_path = root / "bot.sqlite3"
            backup_directory = root / "backups"
            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute("CREATE TABLE marker (value TEXT)")
                connection.execute("INSERT INTO marker VALUES ('preserved')")
                connection.commit()

            config = BackupConfig(
                bot_id="test-bot",
                database_path=database_path,
                local_backup_directory=backup_directory,
                bucket="test-project-sqlite-backups",
                object_prefix="bots/test-bot",
                retention_days=400,
            )
            uploaded: list[tuple[str, str, Path, str]] = []

            def uploader(bucket: str, object_name: str, path: Path, token: str) -> dict[str, object]:
                uploaded.append((bucket, object_name, path, token))
                return {"name": object_name, "size": str(path.stat().st_size)}

            status = run_backup(
                config,
                now=datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc),
                token_provider=lambda: "metadata-token",
                uploader=uploader,
            )

            self.assertEqual(len(uploaded), 2)
            self.assertTrue(uploaded[0][1].startswith("bots/test-bot/2026/07/test-bot-"))
            self.assertTrue(uploaded[0][1].endswith(".sqlite3"))
            self.assertEqual(uploaded[1][1], f"{uploaded[0][1]}.sha256")
            self.assertTrue(all(item[0] == config.bucket and item[3] == "metadata-token" for item in uploaded))
            with closing(sqlite3.connect(uploaded[0][2])) as connection:
                self.assertEqual(connection.execute("SELECT value FROM marker").fetchone(), ("preserved",))
                self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone(), ("ok",))

            status_path = backup_directory / "last-backup-test-bot.json"
            saved_status = json.loads(status_path.read_text(encoding="ascii"))
            self.assertEqual(saved_status, status)
            self.assertEqual(status["integrity"], "ok")
            self.assertEqual(status["objectUri"], f"gs://{config.bucket}/{uploaded[0][1]}")
            self.assertEqual(len(str(status["sha256"])), 64)

    def test_prunes_only_expired_backups_for_the_same_bot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database_path = root / "bot.sqlite3"
            backup_directory = root / "backups"
            backup_directory.mkdir()
            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute("CREATE TABLE marker (value TEXT)")

            old_database = backup_directory / "test-bot-20200101T000000Z-old.sqlite3"
            old_checksum = backup_directory / f"{old_database.name}.sha256"
            foreign_database = backup_directory / "other-bot-20200101T000000Z-old.sqlite3"
            for candidate in (old_database, old_checksum, foreign_database):
                candidate.write_text("old", encoding="ascii")
                old_timestamp = (datetime.now(timezone.utc) - timedelta(days=500)).timestamp()
                os.utime(candidate, (old_timestamp, old_timestamp))

            config = BackupConfig(
                bot_id="test-bot",
                database_path=database_path,
                local_backup_directory=backup_directory,
                bucket="test-project-sqlite-backups",
                object_prefix="bots/test-bot",
                retention_days=400,
            )

            run_backup(
                config,
                now=datetime.now(timezone.utc),
                token_provider=lambda: "token",
                uploader=lambda _bucket, name, path, _token: {"name": name, "size": str(path.stat().st_size)},
            )

            self.assertFalse(old_database.exists())
            self.assertFalse(old_checksum.exists())
            self.assertTrue(foreign_database.exists())

    def test_config_rejects_relative_paths_and_unsafe_prefixes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "botId": "test-bot",
                        "databasePath": "relative.sqlite3",
                        "localBackupDirectory": str(Path(temp_dir).resolve()),
                        "bucket": "test-project-sqlite-backups",
                        "objectPrefix": "bots/../other",
                        "retentionDays": 400,
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_config(config_path)


class SqliteBackupAutomationTests(unittest.TestCase):
    def test_gcp_setup_is_private_scoped_idempotent_and_reusable(self) -> None:
        setup = (PROJECT_ROOT / "scripts" / "deploy" / "Enable-GceSqliteBackups.ps1").read_text(
            encoding="utf-8"
        )
        installer = (PROJECT_ROOT / "deploy" / "gce" / "install-sqlite-backup.sh").read_text(
            encoding="utf-8"
        )
        runtime = (PROJECT_ROOT / "deploy" / "gce" / "sqlite_backup.py").read_text(encoding="utf-8")
        lifecycle = json.loads(
            (PROJECT_ROOT / "deploy" / "gce" / "backup-lifecycle.json").read_text(encoding="utf-8")
        )

        self.assertIn("AcknowledgePotentialStorageCost", setup)
        self.assertIn("roles/storage.objectCreator", setup)
        self.assertIn("uniform-bucket-level-access", setup)
        self.assertIn("public-access-prevention", setup)
        self.assertIn("tunnel-through-iap", setup)
        self.assertNotIn("roles/storage.admin", setup)
        self.assertNotIn("projects add-iam-policy-binding", setup)
        self.assertIn("OnCalendar=monthly", installer)
        self.assertIn("Persistent=true", installer)
        self.assertIn("RandomizedDelaySec=6h", installer)
        self.assertIn("ProtectSystem=strict", installer)
        self.assertIn("useradd --uid", installer)
        self.assertIn("/usr/sbin/nologin", installer)
        self.assertIn("PRAGMA integrity_check", runtime)
        self.assertIn("source.backup(destination)", runtime)
        self.assertIn('"ifGenerationMatch": "0"', runtime)
        self.assertEqual(lifecycle["rule"][0]["condition"]["age"], 400)
        self.assertEqual(lifecycle["rule"][0]["condition"]["matchesPrefix"], ["bots/"])

    def test_runbook_covers_operations_recovery_and_fleet_reuse(self) -> None:
        guide = (PROJECT_ROOT / "docs" / "BACKUPS_GCE.md").read_text(encoding="utf-8")
        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        deploy_guide = (PROJECT_ROOT / "docs" / "DEPLOY_GCE.md").read_text(encoding="utf-8")

        for required_section in (
            "## Modelo de seguridad",
            "### Límite del aislamiento en un bucket compartido",
            "## Costos y capacidad",
            "## Reutilizarlo con otro bot",
            "## Restaurar una copia",
            "## Pausar, reactivar o retirar un bot",
            "## Diagnóstico de fallos",
            "## Criterio de éxito para un bot nuevo",
        ):
            self.assertIn(required_section, guide)
        self.assertIn("last-backup-<bot-id>.json", guide)
        self.assertIn("docs/BACKUPS_GCE.md", readme)
        self.assertIn("BACKUPS_GCE.md", deploy_guide)


if __name__ == "__main__":
    unittest.main()
