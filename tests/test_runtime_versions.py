import platform
from pathlib import Path
import re
import sys
import textwrap
import unittest
from unittest.mock import patch

from galerazo_bot.runtime import ensure_python_version, required_python_version
from scripts.runtime_versions import check_versions


class RuntimeVersionTests(unittest.TestCase):
    def test_automatic_update_refuses_a_runner_older_than_the_project_pin(self) -> None:
        root = Path(__file__).resolve().parent.parent
        workflow = (root / ".github/workflows/runtime-update.yml").read_text(encoding="utf-8")
        guard = re.search(r"python - <<'PY'\n(.*?)\n          PY", workflow, re.DOTALL)
        self.assertIsNotNone(guard)
        code = compile(textwrap.dedent(guard.group(1)), "runtime-update-guard", "exec")
        current = tuple(map(int, required_python_version().split(".")))
        files = {name: (root / name).read_bytes() for name in (".python-version", "Dockerfile")}
        with patch.object(sys, "version_info", (*current[:2], current[2] - 1)):
            with self.assertRaisesRegex(SystemExit, "refusing a runtime downgrade"):
                exec(code, {})
        for candidate in (current, (*current[:2], current[2] + 1)):
            with self.subTest(candidate=candidate), patch.object(sys, "version_info", candidate):
                exec(code, {})
        self.assertEqual(files, {name: (root / name).read_bytes() for name in files})

    def test_running_python_matches_project_and_docker(self) -> None:
        self.assertEqual(required_python_version(), platform.python_version())
        self.assertEqual(check_versions(), [])
        ensure_python_version()


if __name__ == "__main__":
    unittest.main()
