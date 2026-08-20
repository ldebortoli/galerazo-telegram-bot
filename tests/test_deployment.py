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
        self.assertIn(
            "COPY --chown=galerazo:galerazo .python-version ./.python-version",
            runtime_section,
        )
        self.assertIn(
            "COPY --chown=galerazo:galerazo CHANGELOG.md ./CHANGELOG.md",
            runtime_section,
        )
        self.assertNotIn("COPY --chown=galerazo:galerazo . .", runtime_section)

    def test_production_compose_persists_data_without_public_ports(self) -> None:
        compose = (PROJECT_ROOT / "compose.production.yaml").read_text(encoding="utf-8")

        self.assertIn("/srv/galerazo/data", compose)
        self.assertIn("/srv/galerazo/backups", compose)
        self.assertIn("/etc/galerazo/bot.env", compose)
        self.assertIn("restart: unless-stopped", compose)
        self.assertIn("network_mode: host", compose)
        self.assertIn("stop_grace_period: 65s", compose)
        self.assertIn("read_only: true", compose)
        self.assertIn("no-new-privileges:true", compose)
        self.assertNotIn("ports:", compose)
        self.assertNotIn("/var/run/docker.sock", compose)

    def test_remote_log_shortcut_uses_read_only_iap_following(self) -> None:
        watcher = (PROJECT_ROOT / "scripts" / "Watch-GceBotLogs.ps1").read_text(encoding="utf-8")
        launcher = (PROJECT_ROOT / "build_control_panel.ps1").read_text(encoding="utf-8")

        self.assertIn("--tunnel-through-iap", watcher)
        self.assertIn("logs --follow --tail", watcher)
        self.assertIn("Galerazo Bot - Logs.lnk", launcher)
        self.assertIn("Watch-GceBotLogs.ps1", launcher)
        self.assertIn("-NoExit -NoProfile", launcher)


class DeploymentAutomationTests(unittest.TestCase):
    def test_lifecycle_orchestrator_preserves_manual_safety_gates(self) -> None:
        lifecycle = (
            PROJECT_ROOT / "scripts" / "deploy" / "Invoke-GceBotLifecycle.ps1"
        ).read_text(encoding="utf-8")

        for action in (
            "Foundation",
            "Infrastructure",
            "Prepare",
            "Configure",
            "MigrateData",
            "Publish",
            "Deploy",
            "Release",
            "Rollback",
        ):
            self.assertIn(f'"{action}"', lifecycle)
        for script in (
            "Initialize-GcpBot.ps1",
            "New-GceBotInstance.ps1",
            "Initialize-GceHost.ps1",
            "Set-GceBotSecrets.ps1",
            "Migrate-GceBotDatabase.ps1",
            "Publish-DockerImage.ps1",
            "Deploy-Gce.ps1",
            "Rollback-Gce.ps1",
        ):
            self.assertIn(script, lifecycle)
        self.assertIn("AcknowledgeBillableResource", lifecycle)
        self.assertIn("AcknowledgeSecretUpload", lifecycle)
        self.assertIn("AcknowledgeDataMigration", lifecycle)
        self.assertIn("AcknowledgeProductionDeploy", lifecycle)
        self.assertIn("data\\bot.pid", lifecycle)
        self.assertIn("/etc/galerazo/bot.env", lifecycle)
        self.assertIn("/srv/galerazo/data/galerazo.sqlite3", lifecycle)
        self.assertIn("tunnel-through-iap", lifecycle)
        self.assertIn('tag -eq "latest"', lifecycle)
        self.assertNotIn("service-accounts keys create", lifecycle)

    def test_gce_instance_setup_is_private_free_tier_scoped_and_idempotent(self) -> None:
        infrastructure = (
            PROJECT_ROOT / "scripts" / "deploy" / "New-GceBotInstance.ps1"
        ).read_text(encoding="utf-8")

        self.assertIn("AcknowledgeBillableResource", infrastructure)
        self.assertIn('"us-west1", "us-central1", "us-east1"', infrastructure)
        self.assertIn('"compute", "networks", "describe"', infrastructure)
        self.assertIn('"compute", "networks", "create"', infrastructure)
        self.assertIn("--stack-type=IPV4_IPV6", infrastructure)
        self.assertIn("--ipv6-access-type=EXTERNAL", infrastructure)
        self.assertIn("--enable-private-ip-google-access", infrastructure)
        self.assertIn("35.235.240.0/20", infrastructure)
        self.assertIn("roles/iap.tunnelResourceAccessor", infrastructure)
        self.assertIn("roles/compute.osAdminLogin", infrastructure)
        self.assertIn("roles/iam.serviceAccountUser", infrastructure)
        self.assertIn("no-address", infrastructure)
        self.assertIn("--machine-type=e2-micro", infrastructure)
        self.assertIn("--boot-disk-type=pd-standard", infrastructure)
        self.assertIn("--image-family=debian-12", infrastructure)
        self.assertIn("--shielded-secure-boot", infrastructure)
        self.assertIn("--deletion-protection", infrastructure)
        self.assertIn("enable-oslogin=TRUE", infrastructure)
        self.assertNotIn("compute instances delete", infrastructure)
        self.assertNotIn("compute routers nats", infrastructure)

    def test_gce_host_bootstrap_verifies_permissions_without_printing_secrets(self) -> None:
        host_setup = (
            PROJECT_ROOT / "scripts" / "deploy" / "Initialize-GceHost.ps1"
        ).read_text(encoding="utf-8")
        verifier = (
            PROJECT_ROOT / "deploy" / "gce" / "verify-host.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("verify-host.sh", host_setup)
        self.assertIn("sudo bash /tmp/verify-host.sh", host_setup)
        for protected_path in (
            "/srv/galerazo/data",
            "/srv/galerazo/backups",
            "/etc/galerazo",
            "/etc/galerazo/secrets",
            "/etc/galerazo/bot.env",
        ):
            self.assertIn(protected_path, verifier)
        self.assertIn("--expect-pristine", verifier)
        self.assertIn("--expect-configured", verifier)
        self.assertIn("TOKEN_STATE=", verifier)
        self.assertNotIn("cat /etc/galerazo/bot.env", verifier)
        self.assertNotIn("set -x", verifier)

    def test_gce_secret_upload_uses_private_files_and_never_cli_values(self) -> None:
        uploader = (
            PROJECT_ROOT / "scripts" / "deploy" / "Set-GceBotSecrets.ps1"
        ).read_text(encoding="utf-8")
        installer = (
            PROJECT_ROOT / "deploy" / "gce" / "install-config.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("AcknowledgeSecretUpload", uploader)
        self.assertIn("WriteAllText", uploader)
        self.assertIn('$lines -join "`n"', uploader)
        self.assertIn("tunnel-through-iap", uploader)
        self.assertIn("umask 077", uploader)
        self.assertNotIn("${Instance}:~/", uploader)
        self.assertIn("/app/data/galerazo.sqlite3", uploader)
        self.assertIn("[System.IO.File]::Delete", uploader)
        self.assertNotIn('"--command", $token', uploader)
        self.assertNotIn("TELEGRAM_BOT_TOKEN=$token", uploader)
        self.assertIn("modo 0700", installer)
        self.assertIn("bot.env.previous", installer)
        self.assertIn("--expect-configured", installer)
        self.assertNotIn("cat \"${env_upload}\"", installer)

    def test_gce_database_migration_is_consistent_private_and_stopped(self) -> None:
        migration = (
            PROJECT_ROOT / "scripts" / "deploy" / "Migrate-GceBotDatabase.ps1"
        ).read_text(encoding="utf-8")
        installer = (
            PROJECT_ROOT / "deploy" / "gce" / "install-database.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("AcknowledgeDataMigration", migration)
        self.assertIn("create_backup", migration)
        self.assertIn("data\\bot.pid", migration)
        self.assertIn("PRAGMA integrity_check", migration)
        self.assertIn("tunnel-through-iap", migration)
        self.assertIn("umask 077", migration)
        self.assertNotIn("sqlite3-wal", migration)
        self.assertIn("sudo docker ps -q", installer)
        self.assertIn("source.backup(destination)", installer)
        self.assertIn("10001 -g 10001 -m 0600", installer)
        self.assertIn("PRAGMA integrity_check", installer)
        self.assertNotIn("-wal", installer)

    def test_gce_remote_secret_contract_never_returns_existing_values(self) -> None:
        status_script = (
            PROJECT_ROOT / "scripts" / "deploy" / "Get-GceBotSecretStatus.ps1"
        ).read_text(encoding="utf-8")
        patch_script = (
            PROJECT_ROOT / "scripts" / "deploy" / "Patch-GceBotSecrets.ps1"
        ).read_text(encoding="utf-8")
        inspector = (
            PROJECT_ROOT / "deploy" / "gce" / "inspect-secrets.sh"
        ).read_text(encoding="utf-8")
        installer = (
            PROJECT_ROOT / "deploy" / "gce" / "patch-config.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("tunnel-through-iap", status_script)
        self.assertIn("ConvertTo-Json -Compress", status_script)
        self.assertIn("AcknowledgeSecretUpdate", patch_script)
        self.assertIn("32768", patch_script)
        self.assertIn("umask 077", patch_script)
        self.assertIn("secret-patch.json", patch_script)
        for key in (
            "TELEGRAM_HISOPO_COMMON_FILE_ID",
            "TELEGRAM_HISOPO_SILVER_FILE_ID",
            "TELEGRAM_HISOPO_GOLD_FILE_ID",
        ):
            self.assertIn(key, status_script)
            self.assertIn(key, patch_script)
            self.assertIn(key, inspector)
            self.assertIn(key, installer)
        self.assertIn('bool(values.get(key))', inspector)
        self.assertNotIn('print(values', inspector)
        self.assertIn("TELEGRAM_BOT_TOKEN no se puede eliminar", installer)
        self.assertIn("bot_env}.previous", installer)
        self.assertIn("--expect-configured", installer)
        self.assertNotIn("cat \"${patch_upload}\"", installer)

    def test_gcp_bot_foundation_is_idempotent_scoped_and_keyless(self) -> None:
        foundation = (
            PROJECT_ROOT / "scripts" / "deploy" / "Initialize-GcpBot.ps1"
        ).read_text(encoding="utf-8")

        for api in (
            "compute.googleapis.com",
            "artifactregistry.googleapis.com",
            "iap.googleapis.com",
            "iamcredentials.googleapis.com",
        ):
            self.assertIn(api, foundation)
        self.assertIn('repositories", "describe"', foundation)
        self.assertIn('repositories", "create"', foundation)
        self.assertIn('"service-accounts", "describe"', foundation)
        self.assertIn('service-accounts", "create"', foundation)
        self.assertIn("repositories\", \"add-iam-policy-binding", foundation)
        self.assertIn("roles/artifactregistry.reader", foundation)
        self.assertIn("roles/artifactregistry.writer", foundation)
        self.assertIn('"--managed-by=user"', foundation)
        self.assertNotIn("service-accounts keys create", foundation)
        self.assertNotIn("projects add-iam-policy-binding", foundation)
        self.assertNotIn("compute instances create", foundation)

    def test_billing_report_setup_is_confirmed_and_least_privilege(self) -> None:
        setup = (
            PROJECT_ROOT
            / "scripts"
            / "deploy"
            / "Initialize-GceBillingReport.ps1"
        ).read_text(encoding="utf-8")

        self.assertIn("AcknowledgeBillableResource", setup)
        self.assertIn("bigquery.googleapis.com", setup)
        self.assertIn("roles/bigquery.jobUser", setup)
        self.assertIn("roles/bigquery.dataViewer", setup)
        self.assertIn("--dataset", setup)
        self.assertNotIn("service-accounts keys create", setup)

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
        self.assertIn("ensure_python_version", build)
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
        self.assertIn("No previous image exists", deploy)
        self.assertIn('stop bot || true', deploy)
        self.assertIn("--wait-timeout 120", deploy)
        self.assertIn("previous-image.env", rollback)


if __name__ == "__main__":
    unittest.main()
