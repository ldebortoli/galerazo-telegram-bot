import platform
import unittest

from galerazo_bot.runtime import ensure_python_version, required_python_version
from scripts.runtime_versions import check_versions


class RuntimeVersionTests(unittest.TestCase):
    def test_running_python_matches_project_and_docker(self) -> None:
        self.assertEqual(required_python_version(), platform.python_version())
        self.assertEqual(check_versions(), [])
        ensure_python_version()


if __name__ == "__main__":
    unittest.main()
