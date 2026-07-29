import logging
import unittest

from galerazo_bot.logging_utils import SecretRedactionFilter, SuccessfulGetUpdatesFilter, redact_secrets


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

    def test_filter_ignores_only_successful_get_updates(self) -> None:
        log_filter = SuccessfulGetUpdatesFilter()
        successful_poll = logging.LogRecord(
            "httpx",
            logging.INFO,
            __file__,
            1,
            'HTTP Request: POST https://api.telegram.org/bot<redacted>/getUpdates "HTTP/1.1 200 OK"',
            (),
            None,
        )
        send_message = logging.LogRecord(
            "httpx",
            logging.INFO,
            __file__,
            1,
            'HTTP Request: POST https://api.telegram.org/bot<redacted>/sendMessage "HTTP/1.1 200 OK"',
            (),
            None,
        )
        failed_poll = logging.LogRecord(
            "httpx",
            logging.INFO,
            __file__,
            1,
            'HTTP Request: POST https://api.telegram.org/bot<redacted>/getUpdates "HTTP/1.1 500 Internal Server Error"',
            (),
            None,
        )
        self.assertFalse(log_filter.filter(successful_poll))
        self.assertTrue(log_filter.filter(send_message))
        self.assertTrue(log_filter.filter(failed_poll))


if __name__ == "__main__":
    unittest.main()
