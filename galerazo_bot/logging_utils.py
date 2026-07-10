from __future__ import annotations

import logging
import re


TELEGRAM_TOKEN_PATTERN = re.compile(r"(?<!\d)\d{6,}:[A-Za-z0-9_-]{8,}")


def redact_secrets(text: str) -> str:
    return TELEGRAM_TOKEN_PATTERN.sub("<redacted>", text)


class SecretRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_secrets(record.getMessage())
        record.args = ()
        return True


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    for handler in logging.getLogger().handlers:
        if not any(isinstance(item, SecretRedactionFilter) for item in handler.filters):
            handler.addFilter(SecretRedactionFilter())
