from __future__ import annotations

import logging
import re


TELEGRAM_TOKEN_PATTERN = re.compile(r"(?<!\d)\d{6,}:[A-Za-z0-9_-]{8,}")
SUCCESSFUL_GET_UPDATES_PATTERN = re.compile(r'/getUpdates "HTTP/1\.1 200 OK"')


def redact_secrets(text: str) -> str:
    return TELEGRAM_TOKEN_PATTERN.sub("<redacted>", text)


class SecretRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_secrets(record.getMessage())
        record.args = ()
        return True


class SuccessfulGetUpdatesFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not (
            record.name == "httpx"
            and SUCCESSFUL_GET_UPDATES_PATTERN.search(record.getMessage()) is not None
        )


def configure_logging() -> None:
    root_logger = logging.getLogger()
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")
    root_logger.setLevel(logging.DEBUG)
    for handler in root_logger.handlers:
        if not any(isinstance(item, SecretRedactionFilter) for item in handler.filters):
            handler.addFilter(SecretRedactionFilter())
        if not any(isinstance(item, SuccessfulGetUpdatesFilter) for item in handler.filters):
            handler.addFilter(SuccessfulGetUpdatesFilter())
