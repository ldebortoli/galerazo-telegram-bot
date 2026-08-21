import logging
import sys
import unittest

from galerazo_bot.logging_utils import (
    ExceptionFirstFormatter,
    SecretRedactionFilter,
    SuccessfulGetUpdatesFilter,
    exception_summary,
    redact_secrets,
)


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

    def test_exception_summary_and_formatter_put_error_first(self) -> None:
        self.assertEqual(exception_summary(RuntimeError()), "RuntimeError")
        self.assertEqual(exception_summary(RuntimeError("failure")), "RuntimeError: failure")
        formatter = ExceptionFirstFormatter("%(levelname)s %(name)s: %(message)s")
        plain = logging.LogRecord("test", logging.INFO, __file__, 1, "plain", (), None)
        self.assertEqual(formatter.format(plain), "INFO test: plain")

        try:
            raise RuntimeError("token 123456:abcdefgh")
        except RuntimeError:
            exc_info = sys.exc_info()
        record = logging.LogRecord(
            "test",
            logging.ERROR,
            __file__,
            1,
            "operation failed",
            (),
            exc_info,
        )

        formatted = formatter.format(record)

        self.assertTrue(formatted.startswith("RuntimeError: token <redacted>\n"))
        self.assertIn("ERROR test: operation failed", formatted)
        self.assertIn("Traceback (most recent call last)", formatted)
        self.assertNotIn("123456:abcdefgh", formatted)
        self.assertIs(record.exc_info, exc_info)
        self.assertIsNone(record.exc_text)


if __name__ == "__main__":
    unittest.main()
