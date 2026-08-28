from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import gspread
from gspread.exceptions import WorksheetNotFound

from .database import Expense
from .expenses import CardClosingResult, ExpenseMovement


MONTH_NAMES = (
    "ENERO",
    "FEBRERO",
    "MARZO",
    "ABRIL",
    "MAYO",
    "JUNIO",
    "JULIO",
    "AGOSTO",
    "SEPTIEMBRE",
    "OCTUBRE",
    "NOVIEMBRE",
    "DICIEMBRE",
)
PURCHASE_HEADER_ROW = 13
PURCHASE_FIRST_DATA_ROW = 14
DEFAULT_MONTH_DATA_ROWS = 57


@dataclass(frozen=True)
class GoogleSheetsConfig:
    credentials_json_path: Path | None
    spreadsheet_id: str | None
    worksheet_name: str = "Gastos y compras"
    cashflow_sheet_prefix: str = "Gastos"


@dataclass(frozen=True)
class ExpenseSheetWriteResult:
    success: bool
    error: str | None = None
    purchase_sheet_row: int | None = None
    cashflow_sheet_name: str | None = None
    cashflow_sheet_row: int | None = None
    month_created: bool = False


@dataclass(frozen=True)
class _MonthBlock:
    label_row: int
    data_start_row: int
    data_end_row: int


@dataclass(frozen=True)
class _ExpenseWritePlan:
    requests: list[dict]
    purchase_worksheet: object | None
    purchase_row: int | None
    cashflow_worksheet: object | None
    cashflow_sheet_name: str | None
    cashflow_row: int | None
    month_created: bool


class SheetStructureError(RuntimeError):
    pass


class GoogleSheetsExpenseWriter:
    def __init__(self, config: GoogleSheetsConfig) -> None:
        self._config = config
        self._lock = threading.Lock()

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

    def write_expense(self, expense: Expense) -> ExpenseSheetWriteResult:
        if not self.is_configured():
            return ExpenseSheetWriteResult(False, "sheet_not_configured")
        if not self.is_ready():
            return ExpenseSheetWriteResult(False, "sheet_not_ready")

        with self._lock:
            try:
                spreadsheet = self._open_spreadsheet()
                return self._write_expense(spreadsheet, expense)
            except Exception as exc:  # pragma: no cover - external API failures vary
                return ExpenseSheetWriteResult(
                    False,
                    str(exc),
                    expense.purchase_sheet_row,
                    expense.cashflow_sheet_name,
                    expense.cashflow_sheet_row,
                )

    def add_card_closing(self, closing_date: date) -> CardClosingResult:
        if not self.is_configured():
            return CardClosingResult(False, False, error="sheet_not_configured")
        if not self.is_ready():
            return CardClosingResult(True, False, error="sheet_not_ready")

        with self._lock:
            try:
                spreadsheet = self._open_spreadsheet()
                worksheet = self._required_worksheet(spreadsheet, self._config.worksheet_name)
                values = worksheet.col_values(14)
                if any(_same_date(value, closing_date) for value in values[PURCHASE_HEADER_ROW:]):
                    return CardClosingResult(True, False, duplicate=True)
                row_number = max(len(values) + 1, PURCHASE_FIRST_DATA_ROW)
                for _attempt in range(3):
                    if _cell_is_empty(worksheet, row_number, "N"):
                        break
                    values = worksheet.col_values(14)
                    if any(
                        _same_date(value, closing_date)
                        for value in values[PURCHASE_HEADER_ROW:]
                    ):
                        return CardClosingResult(True, False, duplicate=True)
                    row_number = max(len(values) + 1, PURCHASE_FIRST_DATA_ROW)
                else:
                    return CardClosingResult(
                        True,
                        False,
                        error="sheet_target_cell_occupied",
                    )
                requests = []
                if row_number > PURCHASE_FIRST_DATA_ROW:
                    requests.append(
                        _copy_paste_request(
                            worksheet.id,
                            row_number - 1,
                            row_number,
                            13,
                            14,
                            row_number,
                            row_number + 1,
                            "PASTE_FORMAT",
                        )
                    )
                requests.append(
                    _single_cell_request(
                        worksheet.id,
                        row_number,
                        14,
                        _number_value(_google_date_number(closing_date)),
                    )
                )
                spreadsheet.batch_update({"requests": requests})
                return CardClosingResult(True, True, row_number=row_number)
            except Exception as exc:  # pragma: no cover - external API failures vary
                return CardClosingResult(True, False, error=str(exc))

    def _open_spreadsheet(self):
        assert self._config.credentials_json_path is not None
        assert self._config.spreadsheet_id is not None
        client = gspread.service_account(filename=str(self._config.credentials_json_path))
        return client.open_by_key(self._config.spreadsheet_id)

    def _write_expense(self, spreadsheet, expense: Expense) -> ExpenseSheetWriteResult:
        month_created = False
        for attempt in range(3):  # pragma: no branch - every path breaks or returns
            plan = self._plan_expense_write(spreadsheet, expense)
            if isinstance(plan, ExpenseSheetWriteResult):
                return plan
            month_created = month_created or plan.month_created
            occupied = (
                plan.purchase_worksheet is not None
                and plan.purchase_row is not None
                and not _cell_is_empty(plan.purchase_worksheet, plan.purchase_row, "A")
            ) or (
                plan.cashflow_worksheet is not None
                and plan.cashflow_row is not None
                and not _cell_is_empty(plan.cashflow_worksheet, plan.cashflow_row, "A")
            )
            if not occupied:
                break
            if expense.purchase_sheet_row is not None or expense.cashflow_sheet_row is not None:
                return ExpenseSheetWriteResult(
                    False,
                    "sheet_target_row_occupied",
                    expense.purchase_sheet_row,
                    plan.cashflow_sheet_name,
                    expense.cashflow_sheet_row,
                    month_created,
                )
            if attempt == 2:
                return ExpenseSheetWriteResult(
                    False,
                    "sheet_target_row_occupied",
                    cashflow_sheet_name=plan.cashflow_sheet_name,
                    month_created=month_created,
                )
        try:
            spreadsheet.batch_update({"requests": plan.requests})
        except Exception as exc:
            return ExpenseSheetWriteResult(
                False,
                str(exc),
                plan.purchase_row,
                plan.cashflow_sheet_name,
                plan.cashflow_row,
                month_created,
            )
        return ExpenseSheetWriteResult(
            True,
            purchase_sheet_row=plan.purchase_row,
            cashflow_sheet_name=plan.cashflow_sheet_name,
            cashflow_sheet_row=plan.cashflow_row,
            month_created=month_created,
        )

    def _plan_expense_write(
        self,
        spreadsheet,
        expense: Expense,
    ) -> _ExpenseWritePlan | ExpenseSheetWriteResult:
        purchase_worksheet = None
        purchase_row = expense.purchase_sheet_row
        cashflow_worksheet = None
        cashflow_sheet_name = expense.cashflow_sheet_name
        cashflow_row = expense.cashflow_sheet_row
        month_created = False
        requests: list[dict] = []

        if expense.movement_type == ExpenseMovement.PURCHASE:
            purchase_worksheet = self._required_worksheet(spreadsheet, self._config.worksheet_name)
            purchase_row = purchase_row or _next_purchase_row(purchase_worksheet)
            requests.extend(_purchase_requests(purchase_worksheet, purchase_row, expense))

        if expense.include_cashflow:
            occurred_on = date.fromisoformat(expense.occurred_on)
            cashflow_sheet_name = cashflow_sheet_name or (
                f"{self._config.cashflow_sheet_prefix} {occurred_on.year}"
            )
            cashflow_worksheet = self._worksheet_or_none(spreadsheet, cashflow_sheet_name)
            if cashflow_worksheet is None:
                if not expense.opens_cashflow_month:
                    return ExpenseSheetWriteResult(
                        False,
                        "cashflow_month_not_open",
                        purchase_row,
                        cashflow_sheet_name,
                        None,
                    )
                cashflow_worksheet = self._create_year_worksheet(
                    spreadsheet,
                    occurred_on.year,
                    cashflow_sheet_name,
                )
                month_created = True

            block = _find_month_block(cashflow_worksheet, occurred_on.month)
            if block is None:
                if not expense.opens_cashflow_month:
                    return ExpenseSheetWriteResult(
                        False,
                        "cashflow_month_not_open",
                        purchase_row,
                        cashflow_sheet_name,
                        None,
                    )
                block, month_requests = _new_month_requests(cashflow_worksheet, occurred_on.month)
                requests.extend(month_requests)
                month_created = True
            cashflow_row = cashflow_row or _next_cashflow_row(cashflow_worksheet, block)
            requests.extend(_cashflow_requests(cashflow_worksheet, cashflow_row, expense))

        if not requests:
            raise SheetStructureError("El gasto no tiene una hoja de destino.")
        return _ExpenseWritePlan(
            requests,
            purchase_worksheet,
            purchase_row,
            cashflow_worksheet,
            cashflow_sheet_name,
            cashflow_row,
            month_created,
        )

    def _create_year_worksheet(self, spreadsheet, year: int, sheet_name: str):
        previous_name = f"{self._config.cashflow_sheet_prefix} {year - 1}"
        previous = self._required_worksheet(spreadsheet, previous_name)
        january = _find_month_block(previous, 1)
        if january is None:
            raise SheetStructureError(f"{previous_name} no contiene el bloque de ENERO.")

        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=999, cols=26)
        try:
            copy_end_row = january.data_end_row + 1
            requests = [
                _copy_paste_request(
                    previous.id,
                    1,
                    copy_end_row,
                    0,
                    10,
                    1,
                    copy_end_row,
                    "PASTE_NORMAL",
                    destination_sheet_id=worksheet.id,
                ),
                _clear_values_request(
                    worksheet.id,
                    january.data_start_row,
                    january.data_end_row + 1,
                    0,
                    5,
                ),
            ]
            spreadsheet.batch_update({"requests": requests})
        except Exception:
            spreadsheet.del_worksheet(worksheet)
            raise
        return worksheet

    @staticmethod
    def _worksheet_or_none(spreadsheet, name: str):
        try:
            return spreadsheet.worksheet(name)
        except WorksheetNotFound:
            return None

    @staticmethod
    def _required_worksheet(spreadsheet, name: str):
        try:
            return spreadsheet.worksheet(name)
        except WorksheetNotFound as exc:
            raise SheetStructureError(f"No existe la hoja requerida: {name}.") from exc


def _next_purchase_row(worksheet) -> int:
    values = worksheet.col_values(1)
    last_used_row = PURCHASE_HEADER_ROW
    for row_number, value in enumerate(values, start=1):
        if row_number >= PURCHASE_FIRST_DATA_ROW and str(value).strip():
            last_used_row = row_number
    row_number = last_used_row + 1
    if row_number > worksheet.row_count:
        worksheet.add_rows(max(1000, row_number - worksheet.row_count))
    return row_number


def _purchase_requests(worksheet, row_number: int, expense: Expense) -> list[dict]:
    amount = Decimal(expense.amount_cents) / Decimal(100)
    row_values = [
        _number_value(_google_date_number(date.fromisoformat(expense.occurred_on))),
        _string_value(expense.category),
        _string_value(expense.author),
        _string_value(expense.description),
        _string_value(expense.payment_method),
    ]
    if expense.currency == "USD":
        row_values.extend(
            [
                _string_value("----"),
                _string_value("----"),
                _number_value(amount),
                _number_value(1),
                _number_value(amount),
            ]
        )
    else:
        if expense.usd_rate is None:
            raise SheetStructureError("El gasto en pesos no tiene cotización USD.")
        row_values.extend(
            [
                _number_value(amount),
                _number_value(Decimal(expense.usd_rate)),
                _formula_value(f"=IF(G{row_number}=0, 0, F{row_number}/G{row_number})"),
                _number_value(expense.installments),
                _formula_value(f'=IF(I{row_number}=0, "----", F{row_number}/I{row_number})'),
            ]
        )
    row_values.extend(
        [
            _formula_value(
                f'=IF(I{row_number}=0, "----", MINIFS($N$14:N, $N$14:N, ">="&A{row_number}))'
            ),
            _formula_value(
                f'=IF(I{row_number}=0, "----", IF(DAY(K{row_number}) <= 15, '
                f"EOMONTH(K{row_number}, -1) + 1, EOMONTH(K{row_number}, 0) + 1))"
            ),
            _formula_value(
                f'=IF(OR(A{row_number}="", I{row_number}=""), "", IF(I{row_number}=0, '
                f"EOMONTH(A{row_number}, -1) + 1, EDATE(L{row_number}, I{row_number}-1)))"
            ),
        ]
    )
    return [
        _copy_paste_request(
            worksheet.id,
            max(PURCHASE_HEADER_ROW, row_number - 1),
            max(PURCHASE_HEADER_ROW, row_number - 1) + 1,
            0,
            13,
            row_number,
            row_number + 1,
            "PASTE_FORMAT",
        ),
        _row_update_request(worksheet.id, row_number, 1, row_values),
    ]


def _find_month_block(worksheet, month: int) -> _MonthBlock | None:
    blocks = _find_month_blocks(worksheet)
    return blocks.get(month)


def _find_month_blocks(worksheet) -> dict[int, _MonthBlock]:
    values = worksheet.get(
        f"D1:F{worksheet.row_count}",
        value_render_option="FORMULA",
        pad_values=True,
    )
    label_rows: list[tuple[int, int]] = []
    month_by_name = {name: index + 1 for index, name in enumerate(MONTH_NAMES)}
    for row_number, row in enumerate(values, start=1):
        label = str(row[0]).strip().upper() if row else ""
        if label in month_by_name:
            label_rows.append((month_by_name[label], row_number))

    blocks: dict[int, _MonthBlock] = {}
    for index, (month, label_row) in enumerate(label_rows):
        data_start = label_row + 2
        if index + 1 < len(label_rows):
            data_end = label_rows[index + 1][1] - 1
        else:
            data_end = _last_reserved_formula_row(values, data_start)
        blocks[month] = _MonthBlock(label_row, data_start, data_end)
    return blocks


def _last_reserved_formula_row(values: list[list], data_start: int) -> int:
    fallback = data_start + DEFAULT_MONTH_DATA_ROWS - 1
    last_nonempty = None
    for row_number in range(data_start, len(values) + 1):
        row = values[row_number - 1]
        formula_or_value = str(row[2]).strip() if len(row) > 2 else ""
        if not formula_or_value:
            break
        last_nonempty = row_number
    return last_nonempty or fallback


def _new_month_requests(worksheet, month: int) -> tuple[_MonthBlock, list[dict]]:
    blocks = _find_month_blocks(worksheet)
    if not blocks:
        raise SheetStructureError("La hoja anual no contiene bloques mensuales.")
    last_month = max(blocks)
    if month != last_month + 1:
        raise SheetStructureError("Los meses deben abrirse en orden cronológico.")
    source = blocks[last_month]
    height = source.data_end_row - source.label_row + 1
    label_row = source.data_end_row + 1
    data_start = label_row + 2
    data_end = label_row + height - 1
    if data_end > worksheet.row_count:
        worksheet.add_rows(max(100, data_end - worksheet.row_count))
    requests = [
        _copy_paste_request(
            worksheet.id,
            source.label_row,
            source.data_end_row + 1,
            0,
            10,
            label_row,
            data_end + 1,
            "PASTE_NORMAL",
        ),
        _clear_values_request(worksheet.id, data_start, data_end + 1, 0, 5),
        _single_cell_request(
            worksheet.id,
            label_row,
            4,
            _string_value(MONTH_NAMES[month - 1]),
        ),
    ]
    return _MonthBlock(label_row, data_start, data_end), requests


def _next_cashflow_row(worksheet, block: _MonthBlock) -> int:
    values = worksheet.get(f"A{block.data_start_row}:A{block.data_end_row}", pad_values=True)
    last_used_row = block.data_start_row - 1
    for offset in range(block.data_end_row - block.data_start_row + 1):
        value = values[offset][0] if offset < len(values) and values[offset] else ""
        if str(value).strip():
            last_used_row = block.data_start_row + offset
    next_row = last_used_row + 1
    if next_row > block.data_end_row:
        raise SheetStructureError("El bloque mensual no tiene filas libres.")
    return next_row


def _cell_is_empty(worksheet, row_number: int, column_letter: str) -> bool:
    values = worksheet.get(
        f"{column_letter}{row_number}:{column_letter}{row_number}",
        value_render_option="FORMULA",
        pad_values=True,
    )
    value = values[0][0] if values and values[0] else ""
    return not str(value).strip()


def _cashflow_requests(worksheet, row_number: int, expense: Expense) -> list[dict]:
    amount = Decimal(expense.amount_cents) / Decimal(100)
    description = expense.description
    if expense.movement_type == ExpenseMovement.CARD_STATEMENT:
        description = f"{expense.category}: {description}"
    values = [
        _number_value(_google_date_number(date.fromisoformat(expense.occurred_on))),
        _string_value(description),
        _string_value(expense.payment_method),
    ]
    if expense.currency == "USD":
        values.extend([_string_value("----"), _string_value("----"), _number_value(amount)])
    else:
        if expense.usd_rate is None:
            raise SheetStructureError("El gasto en pesos no tiene cotización USD.")
        values.extend(
            [
                _number_value(amount),
                _number_value(Decimal(expense.usd_rate)),
                _formula_value(f"=IF(E{row_number}=0, 0, D{row_number}/E{row_number})"),
            ]
        )
    # Every reserved row in an annual sheet is already formatted by the month
    # template. Copying the previous row would apply the header style to the
    # first expense of a newly opened month.
    return [_row_update_request(worksheet.id, row_number, 1, values)]


def _row_update_request(sheet_id: int, row_number: int, start_column: int, values: list[dict]) -> dict:
    return {
        "updateCells": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": row_number - 1,
                "endRowIndex": row_number,
                "startColumnIndex": start_column - 1,
                "endColumnIndex": start_column - 1 + len(values),
            },
            "rows": [{"values": values}],
            "fields": "userEnteredValue",
        }
    }


def _single_cell_request(sheet_id: int, row_number: int, column_number: int, value: dict) -> dict:
    return _row_update_request(sheet_id, row_number, column_number, [value])


def _clear_values_request(
    sheet_id: int,
    start_row: int,
    end_row: int,
    start_column: int,
    end_column: int,
) -> dict:
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": start_row - 1,
                "endRowIndex": end_row - 1,
                "startColumnIndex": start_column,
                "endColumnIndex": end_column,
            },
            "cell": {},
            "fields": "userEnteredValue",
        }
    }


def _copy_paste_request(
    sheet_id: int,
    source_start_row: int,
    source_end_row: int,
    source_start_column: int,
    source_end_column: int,
    destination_start_row: int,
    destination_end_row: int,
    paste_type: str,
    *,
    destination_sheet_id: int | None = None,
) -> dict:
    return {
        "copyPaste": {
            "source": {
                "sheetId": sheet_id,
                "startRowIndex": source_start_row - 1,
                "endRowIndex": source_end_row - 1,
                "startColumnIndex": source_start_column,
                "endColumnIndex": source_end_column,
            },
            "destination": {
                "sheetId": destination_sheet_id or sheet_id,
                "startRowIndex": destination_start_row - 1,
                "endRowIndex": destination_end_row - 1,
                "startColumnIndex": source_start_column,
                "endColumnIndex": source_end_column,
            },
            "pasteType": paste_type,
            "pasteOrientation": "NORMAL",
        }
    }


def _string_value(value: str) -> dict:
    return {"userEnteredValue": {"stringValue": value}}


def _number_value(value: Decimal | int | float) -> dict:
    return {"userEnteredValue": {"numberValue": float(value)}}


def _formula_value(value: str) -> dict:
    return {"userEnteredValue": {"formulaValue": value}}


def _google_date_number(value: date) -> int:
    return (value - date(1899, 12, 30)).days


def _same_date(raw: object, expected: date) -> bool:
    text = str(raw).strip()
    for pattern in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, pattern).date() == expected
        except ValueError:
            pass
    return False
