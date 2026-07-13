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


if __name__ == "__main__":
    unittest.main()
