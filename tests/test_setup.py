from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class WindowsSetupTests(unittest.TestCase):
    def test_setup_orchestrates_runtime_config_build_and_panel(self) -> None:
        setup = (PROJECT_ROOT / "scripts" / "setup.ps1").read_text(encoding="utf-8")

        self.assertIn("sync_windows_runtime.ps1", setup)
        self.assertIn("build_control_panel.ps1", setup)
        self.assertIn('if (-not (Test-Path -LiteralPath $envPath))', setup)
        self.assertIn("Copy-Item -LiteralPath $envExamplePath -Destination $envPath", setup)
        self.assertIn("Start-Process -FilePath $launcherPath", setup)
        self.assertIn("[switch]$NoLaunch", setup)

    def test_runtime_sync_reuses_valid_environment_and_supports_clean_rebuild(self) -> None:
        runtime = (PROJECT_ROOT / "scripts" / "sync_windows_runtime.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn("[switch]$ForceRecreate", runtime)
        self.assertIn("[switch]$SkipTests", runtime)
        self.assertIn(".venv ya usa Python", runtime)
        self.assertIn("ReparsePoint", runtime)
        self.assertIn("compileall", runtime)
        self.assertIn("pip check", runtime)

    def test_panel_build_creates_codex_apps_and_desktop_shortcuts(self) -> None:
        build = (PROJECT_ROOT / "build_control_panel.ps1").read_text(encoding="utf-8")

        self.assertIn('"CODEX APPS"', build)
        self.assertIn("DesktopDirectory", build)
        self.assertIn('"Galerazo Bot.lnk"', build)
        self.assertIn("GalerazoBotControl.exe", build)

    def test_double_click_installer_routes_to_versioned_setup(self) -> None:
        installer = (
            PROJECT_ROOT / "instaladores" / "Instalar Galerazo Bot.cmd"
        ).read_text(encoding="utf-8")

        self.assertIn("scripts\\setup.ps1", installer)
        self.assertIn("ExecutionPolicy Bypass", installer)
        self.assertIn("%*", installer)


if __name__ == "__main__":
    unittest.main()
