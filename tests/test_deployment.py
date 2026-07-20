from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from galerazo_bot.deploy_backup import create_deploy_backup
from galerazo_bot.healthcheck import check_database, main as healthcheck_main


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ContainerRuntimeTests(unittest.TestCase):
    def test_healthcheck_opens_sqlite_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "galerazo.sqlite3"
            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute("CREATE TABLE marker (value TEXT)")
                connection.commit()

            with patch.dict(os.environ, {"DATABASE_PATH": str(database_path)}):
                check_database()
                self.assertEqual(healthcheck_main(), 0)

    def test_deploy_backup_uses_sqlite_backup_api(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database_path = root / "galerazo.sqlite3"
            backups_path = root / "backups"
            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute("CREATE TABLE marker (value TEXT)")
                connection.execute("INSERT INTO marker VALUES ('ok')")
                connection.commit()

            with patch.dict(
                os.environ,
                {
                    "DATABASE_PATH": str(database_path),
                    "BACKUPS_PATH": str(backups_path),
                },
            ):
                backup_path = create_deploy_backup()

            self.assertTrue(backup_path.is_file())
            with closing(sqlite3.connect(backup_path)) as connection:
                self.assertEqual(connection.execute("SELECT value FROM marker").fetchone(), ("ok",))

    def test_runtime_image_is_minimal_non_root_and_healthchecked(self) -> None:
        dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("AS test", dockerfile)
        self.assertIn("AS runtime", dockerfile)
        self.assertIn("USER galerazo", dockerfile)
        self.assertIn("/app/data /app/backups", dockerfile)
        self.assertIn("galerazo_bot.healthcheck", dockerfile)
        runtime_section = dockerfile.split("FROM base AS runtime", 1)[1]
        self.assertNotIn("COPY --chown=galerazo:galerazo . .", runtime_section)

    def test_production_compose_persists_data_without_public_ports(self) -> None:
        compose = (PROJECT_ROOT / "compose.production.yaml").read_text(encoding="utf-8")

        self.assertIn("/srv/galerazo/data", compose)
        self.assertIn("/srv/galerazo/backups", compose)
        self.assertIn("/etc/galerazo/bot.env", compose)
        self.assertIn("restart: unless-stopped", compose)
        self.assertIn("read_only: true", compose)
        self.assertIn("no-new-privileges:true", compose)
        self.assertNotIn("ports:", compose)
        self.assertNotIn("/var/run/docker.sock", compose)


class DeploymentAutomationTests(unittest.TestCase):
    def test_github_image_publication_is_manual_and_keyless(self) -> None:
        workflow = (
            PROJECT_ROOT / ".github" / "workflows" / "publish-gce-image.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("\n  push:", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("google-github-actions/auth@v3", workflow)
        self.assertIn("workload_identity_provider", workflow)
        self.assertIn("target: runtime", workflow)
        self.assertIn("platforms: linux/amd64", workflow)
        self.assertNotIn("credentials_json", workflow)
        self.assertNotIn("service_account_key", workflow)

    def test_local_build_and_publish_use_the_same_runtime_target(self) -> None:
        build = (
            PROJECT_ROOT / "scripts" / "deploy" / "Build-DockerImage.ps1"
        ).read_text(encoding="utf-8")
        publish = (
            PROJECT_ROOT / "scripts" / "deploy" / "Publish-DockerImage.ps1"
        ).read_text(encoding="utf-8")

        self.assertIn('"linux/amd64"', build)
        self.assertIn('"--target", "runtime"', build)
        self.assertIn('"--target", "test"', build)
        self.assertIn("auth", publish)
        self.assertIn("configure-docker", publish)
        self.assertIn("last-image.txt", publish)

    def test_remote_deploy_backs_up_and_rolls_back_failed_release(self) -> None:
        deploy = (PROJECT_ROOT / "deploy" / "gce" / "deploy.sh").read_text(
            encoding="utf-8"
        )
        rollback = (PROJECT_ROOT / "deploy" / "gce" / "rollback.sh").read_text(
            encoding="utf-8"
        )

        backup_index = deploy.index("galerazo_bot.deploy_backup")
        pull_index = deploy.index('docker compose -f "${compose_file}" pull bot')
        self.assertLess(backup_index, pull_index)
        self.assertIn("previous-image.env", deploy)
        self.assertIn("Restoring", deploy)
        self.assertIn("--wait-timeout 120", deploy)
        self.assertIn("previous-image.env", rollback)


if __name__ == "__main__":
    unittest.main()
