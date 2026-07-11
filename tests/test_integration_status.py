import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from galerazo_bot.integration_status import load_logging_status, save_logging_status


class IntegrationStatusTests(unittest.TestCase):
    def test_round_trip_logging_warning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            status_path = Path(directory) / "status.json"
            with patch("galerazo_bot.integration_status.STATUS_PATH", status_path):
                save_logging_status(False, "Sin permisos")
                status = load_logging_status()

            self.assertEqual(status["ok"], False)
            self.assertEqual(status["detail"], "Sin permisos")


if __name__ == "__main__":
    unittest.main()
