from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    import gspread
except ModuleNotFoundError:
    gspread = None


EXPENSE_HEADERS = (
    "expense_id",
    "created_at",
    "chat_id",
    "chat_title",
    "user_id",
    "username",
    "display_name",
    "amount",
    "currency",
    "payment_method",
    "source",
    "description",
)


@dataclass(frozen=True)
class GoogleSheetsConfig:
    credentials_json_path: Path | None
    spreadsheet_id: str | None
    worksheet_name: str


class GoogleSheetsExpenseWriter:
    def __init__(self, config: GoogleSheetsConfig) -> None:
        self._config = config

    @property
    def worksheet_name(self) -> str:
        return self._config.worksheet_name

    def is_configured(self) -> bool:
        return bool(self._config.credentials_json_path and self._config.spreadsheet_id)

    def is_ready(self) -> bool:
        if gspread is None or not self.is_configured():
            return False
        credentials_path = self._config.credentials_json_path
        return credentials_path is not None and credentials_path.exists()

    def append_expense_row(self, row: Iterable[str]) -> tuple[bool, str | None]:
        if not self.is_configured():
            return False, "sheet_not_configured"
        if not self.is_ready():
            return False, "sheet_not_ready"

        assert self._config.credentials_json_path is not None
        assert self._config.spreadsheet_id is not None

        try:
            client = gspread.service_account(filename=str(self._config.credentials_json_path))
            spreadsheet = client.open_by_key(self._config.spreadsheet_id)
            worksheet = self._get_or_create_worksheet(spreadsheet)
            self._ensure_headers(worksheet)
            worksheet.append_row(list(row), value_input_option="USER_ENTERED")
        except Exception as exc:  # pragma: no cover - depends on external API
            return False, str(exc)

        return True, None

    def _get_or_create_worksheet(self, spreadsheet):
        try:
            return spreadsheet.worksheet(self._config.worksheet_name)
        except Exception:
            return spreadsheet.add_worksheet(title=self._config.worksheet_name, rows=1000, cols=len(EXPENSE_HEADERS))

    def _ensure_headers(self, worksheet) -> None:
        values = worksheet.get("A1:L1")
        if values and values[0]:
            return
        worksheet.append_row(list(EXPENSE_HEADERS), value_input_option="RAW")
