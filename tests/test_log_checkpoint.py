import tempfile
import unittest
from pathlib import Path

from galerazo_bot.log_checkpoint import check_log


class LogCheckpointTests(unittest.TestCase):
    def test_reads_only_new_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / "bot.log"
            checkpoint = root / "checkpoint.json"
            log.write_bytes(b"INFO started\n")

            first = check_log(log, checkpoint)
            self.assertEqual(first.new_text, "INFO started\n")
            self.assertTrue(first.advanced)

            log.write_bytes(b"INFO started\nINFO update\n")
            second = check_log(log, checkpoint)
            self.assertEqual(second.new_text, "INFO update\n")

    def test_error_requires_acknowledgement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / "bot.log"
            checkpoint = root / "checkpoint.json"
            log.write_bytes(b"ERROR telegram: Conflict: another poller\n")

            failed = check_log(log, checkpoint)
            self.assertFalse(failed.advanced)
            self.assertEqual(len(failed.error_lines), 1)

            acknowledged = check_log(log, checkpoint, acknowledge=True)
            self.assertTrue(acknowledged.advanced)
            self.assertEqual(check_log(log, checkpoint).new_text, "")


if __name__ == "__main__":
    unittest.main()
