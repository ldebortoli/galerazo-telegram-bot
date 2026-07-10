import logging
import unittest

from galerazo_bot.logging_utils import SecretRedactionFilter, redact_secrets


class LoggingUtilsTests(unittest.TestCase):
    def test_redacts_telegram_token_from_url(self) -> None:
        text = "POST https://api.telegram.org/bot123456:ABC_def-ghi-secret/getUpdates"
        self.assertEqual(
            redact_secrets(text),
            "POST https://api.telegram.org/bot<redacted>/getUpdates",
        )

    def test_filter_redacts_formatted_log_arguments(self) -> None:
        record = logging.LogRecord(
            "test",
            logging.INFO,
            __file__,
            1,
            "Request %s",
            ("/bot123456:secret-value/getUpdates",),
            None,
        )
        SecretRedactionFilter().filter(record)
        self.assertEqual(record.getMessage(), "Request /bot<redacted>/getUpdates")


if __name__ == "__main__":
    unittest.main()
