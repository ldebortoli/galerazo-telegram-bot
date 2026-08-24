from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RuntimeUpdateWorkflowTests(unittest.TestCase):
    def test_monthly_dependency_updater_is_isolated_and_fully_validated(self) -> None:
        script = (
            PROJECT_ROOT / "scripts" / "deploy" / "Update-Dependencies.ps1"
        ).read_text(encoding="utf-8")

        self.assertIn("galerazo-dependency-update-", script)
        self.assertIn('"--upgrade-strategy", "eager"', script)
        self.assertIn("pip freeze", script)
        self.assertIn("git diff --quiet -- requirements.txt", script)
        self.assertGreater(script.index('Assert-Command -Name "docker"'), script.index("if ($dependencyDiff -eq 0)"))
        self.assertIn('"coverage", "run", "-m", "pytest"', script)
        self.assertIn('"-m", "pip", "check"', script)
        self.assertIn("Build-DockerImage.ps1", script)
        self.assertIn("finally", script)
        self.assertNotIn("git commit", script)
        self.assertNotIn("git push", script)

        requirements_input = (PROJECT_ROOT / "requirements.in").read_text(encoding="utf-8")
        self.assertIn("colorama\n", requirements_input)

    def test_validated_update_does_not_require_pull_request_permissions(self) -> None:
        workflow = (
            PROJECT_ROOT / ".github" / "workflows" / "runtime-update.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("docker build", workflow)
        self.assertIn("--target runtime", workflow)
        self.assertIn("ensure_python_version", workflow)
        self.assertNotIn("galerazo-bot:update-test python -m pytest", workflow)
        self.assertIn("git push origin HEAD:main", workflow)
        self.assertNotIn("pull-requests: write", workflow)
        self.assertNotIn("gh pr create", workflow)
        self.assertNotIn("--force", workflow)

    def test_quality_runs_tests_once_with_coverage_thresholds(self) -> None:
        workflow = (
            PROJECT_ROOT / ".github" / "workflows" / "quality.yml"
        ).read_text(encoding="utf-8")

        self.assertEqual(workflow.count("coverage run -m pytest"), 1)
        self.assertNotIn("unittest discover", workflow)
        self.assertIn("python -m coverage run", workflow)
        self.assertIn("python scripts/check_coverage.py", workflow)

    def test_all_automated_runners_use_pytest(self) -> None:
        files = (
            PROJECT_ROOT / ".github" / "workflows" / "docker-quality.yml",
            PROJECT_ROOT / ".github" / "workflows" / "runtime-update.yml",
            PROJECT_ROOT / "scripts" / "sync_windows_runtime.ps1",
            PROJECT_ROOT / "scripts" / "deploy" / "Build-DockerImage.ps1",
        )
        for path in files:
            with self.subTest(path=path):
                content = path.read_text(encoding="utf-8")
                self.assertTrue("-m pytest" in content or '"pytest"' in content)
                self.assertNotIn("unittest discover", content)

    def test_pytest_configuration_covers_existing_suite_and_async_tests(self) -> None:
        configuration = (PROJECT_ROOT / "pytest.ini").read_text(encoding="utf-8")

        self.assertIn("testpaths = tests", configuration)
        self.assertIn("asyncio_mode = auto", configuration)


if __name__ == "__main__":
    unittest.main()
