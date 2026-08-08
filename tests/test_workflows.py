from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RuntimeUpdateWorkflowTests(unittest.TestCase):
    def test_validated_update_does_not_require_pull_request_permissions(self) -> None:
        workflow = (
            PROJECT_ROOT / ".github" / "workflows" / "runtime-update.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("docker build", workflow)
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
