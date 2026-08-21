from __future__ import annotations

import logging
import re


TELEGRAM_TOKEN_PATTERN = re.compile(r"(?<!\d)\d{6,}:[A-Za-z0-9_-]{8,}")
SUCCESSFUL_GET_UPDATES_PATTERN = re.compile(r'/getUpdates "HTTP/1\.1 200 OK"')
LOG_FORMAT = "%(levelname)s %(name)s: %(message)s"


def redact_secrets(text: str) -> str:
    return TELEGRAM_TOKEN_PATTERN.sub("<redacted>", text)


def exception_summary(exc: BaseException) -> str:
    detail = str(exc).strip()
    summary = type(exc).__name__
    if detail:
        summary = f"{summary}: {detail}"
    return redact_secrets(summary)


class ExceptionFirstFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if not record.exc_info:
            return redact_secrets(super().format(record))

        exc_info = record.exc_info
        previous_exc_text = record.exc_text
        record.exc_info = None
        record.exc_text = None
        try:
            message = super().format(record)
        finally:
            record.exc_info = exc_info
            record.exc_text = previous_exc_text

        summary = exception_summary(exc_info[1])
        trace = self.formatException(exc_info)
        return redact_secrets(f"{summary}\n{message}\n{trace}")


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
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
    root_logger.setLevel(logging.DEBUG)
    formatter = ExceptionFirstFormatter(LOG_FORMAT)
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)
        if not any(isinstance(item, SecretRedactionFilter) for item in handler.filters):
            handler.addFilter(SecretRedactionFilter())
        if not any(isinstance(item, SuccessfulGetUpdatesFilter) for item in handler.filters):
            handler.addFilter(SuccessfulGetUpdatesFilter())
