from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
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
        self.assertNotIn(" mini_app ", runtime_section)
        self.assertNotIn("EXPOSE 8080", runtime_section)


    def test_mini_app_tunnel_is_loopback_and_secrets_stay_out_of_build_context(self):
        ignored = (PROJECT_ROOT / ".dockerignore").read_text().splitlines()
        for entry in (".codex/", "AGENTS.md", ".env.*", "secrets/", "*.key"):
            self.assertIn(entry, ignored)
        tunnel = (PROJECT_ROOT / "deploy/vps/tunnel.yaml").read_text()
        self.assertIn("127.0.0.1:20241", tunnel)
        self.assertIn("--token-file", tunnel)
        self.assertIn("/run/secrets/tunnel-token:ro", tunnel)
        self.assertNotIn("/etc/galerazo/bot.env", tunnel)
        self.assertNotIn("docker.sock", tunnel)
        ingress = json.loads((PROJECT_ROOT / "deploy/vps/miniapp-tunnel-config.example.json").read_text())["config"]["ingress"]
        self.assertEqual(ingress[0]["service"], "http://127.0.0.1:8080")
        self.assertEqual(ingress[-1], {"service": "http_status:404"})

    def test_local_build_validates_both_container_targets(self):
        build = (PROJECT_ROOT / "scripts/deploy/Build-DockerImage.ps1").read_text()
        for argument in ('"linux/amd64"', '"--target", "runtime"', '"--target", "test"', 'ensure_python_version'):
            self.assertIn(argument, build)

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

    def test_production_compose_can_be_rendered(self) -> None:
        if shutil.which("docker") is None:
            self.skipTest("Docker Compose CLI no disponible")
        environment = os.environ.copy()
        environment["GALERAZO_IMAGE"] = "galerazobot:validation-only"
        compose = (PROJECT_ROOT / "compose.production.yaml").read_text(encoding="utf-8")
        production_env_path = "/etc/galerazo/bot.env"
        self.assertEqual(compose.count(production_env_path), 1)
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture_root = Path(temp_dir)
            fixture_env = fixture_root / "bot.env"
            fixture_env.write_text("", encoding="utf-8")
            fixture_compose = fixture_root / "compose.production.yaml"
            fixture_compose.write_text(
                compose.replace(production_env_path, fixture_env.as_posix()),
                encoding="utf-8",
            )
            result = subprocess.run(
                ["docker", "compose", "-f", str(fixture_compose),
                 "config", "--no-env-resolution", "--quiet"],
                cwd=PROJECT_ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)





class DockerStartupTests(unittest.TestCase):
    def test_docker_startup_preserves_linux_requirement_and_times_out(self) -> None:
        powershell = shutil.which("powershell.exe")
        if powershell is None:
            self.skipTest("Docker Desktop startup is Windows-specific")
        helper = PROJECT_ROOT / "scripts/deploy/Ensure-DockerEngine.ps1"
        scenarios = (
            ("ready", "OK calls=1 starts=0"),
            ("starts", "OK calls=2 starts=1"),
            ("delayed", "OK calls=3 starts=1"),
            ("timeout", "ERROR Docker Desktop no habilito el motor Linux en 0 segundos"),
            ("start-fails", "ERROR No se pudo iniciar Docker Desktop (codigo 1)"),
            ("windows", "ERROR Docker usa 'windows'; se requieren contenedores Linux"),
        )
        for mode, expected in scenarios:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                script = Path(temporary) / "docker-fixture.ps1"
                script.write_text(
                    "param([string]$Helper, [string]$Mode)\n"
                    "$ErrorActionPreference='Stop'\n"
                    "$global:calls=0; $global:starts=0\n"
                    "function docker {\n"
                    "  $global:LASTEXITCODE=0\n"
                    "  if ($args[0] -eq 'desktop') {\n"
                    "    if (($args -join ' ') -ne 'desktop start --detach') { throw 'unexpected mutation' }\n"
                    "    $global:starts++\n"
                    "    if ($Mode -eq 'start-fails') { $global:LASTEXITCODE=1 }; return\n"
                    "  }\n"
                    "  if (($args -join ' ') -ne 'info --format {{.OSType}}') { throw 'unexpected command' }\n"
                    "  $global:calls++\n"
                    "  if ($Mode -eq 'windows') { 'windows'; return }\n"
                    "  if ($Mode -eq 'ready' -or ($Mode -eq 'starts' -and $global:calls -gt 1) -or ($Mode -eq 'delayed' -and $global:calls -gt 2)) { 'linux'; return }\n"
                    "  $global:LASTEXITCODE=1\n"
                    "}\n"
                    "function Start-Sleep { param([int]$Seconds); if ($Seconds -ne 2) { throw 'unexpected delay' } }\n"
                    ". $Helper\n"
                    "$wait = if ($Mode -eq 'delayed') { 2 } else { 0 }\n"
                    "try { Wait-DockerLinuxEngine -TimeoutSeconds $wait; Write-Output \"OK calls=$global:calls starts=$global:starts\" }\n"
                    "catch { Write-Output \"ERROR $($_.Exception.Message)\" }\n",
                    encoding="utf-8",
                )
                result = subprocess.run(
                    [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), str(helper), mode],
                    capture_output=True, text=True, timeout=30, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(expected, result.stdout)


if __name__ == "__main__":
    unittest.main()
