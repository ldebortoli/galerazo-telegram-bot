from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from .i18n import DEFAULT_LANGUAGE, t


DEFAULT_EXPENSE_CURRENCY = "ARS"
DEFAULT_EXPENSE_LIST_LIMIT = 20


@dataclass(frozen=True)
class ExpenseDraft:
    amount_cents: int
    currency: str
    payment_method: str
    source: str
    description: str


@dataclass(frozen=True)
class ExpenseSubmissionResult:
    expense_id: int
    synced: bool
    configured: bool
    error: str | None = None


@dataclass(frozen=True)
class ExpenseSyncResult:
    configured: bool
    synced_count: int
    failed_count: int
    last_error: str | None = None


@dataclass(frozen=True)
class ExpenseSheetStatus:
    configured: bool
    ready: bool
    worksheet_name: str | None
    pending_count: int
    detail: str | None = None


def parse_expense_command_args(raw_args: str) -> ExpenseDraft | None:
    parts = [part.strip() for part in raw_args.split("|")]
    if len(parts) != 4 or any(not part for part in parts):
        return None

    amount_cents = parse_amount_to_cents(parts[0])
    if amount_cents is None or amount_cents <= 0:
        return None

    return ExpenseDraft(
        amount_cents=amount_cents,
        currency=DEFAULT_EXPENSE_CURRENCY,
        payment_method=parts[1],
        source=parts[2],
        description=parts[3],
    )


def parse_amount_to_cents(raw_amount: str) -> int | None:
    cleaned = (
        raw_amount.strip()
        .replace("$", "")
        .replace("ARS", "")
        .replace("ars", "")
        .replace(" ", "")
    )
    if not cleaned:
        return None

    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            normalized = cleaned.replace(".", "").replace(",", ".")
        else:
            normalized = cleaned.replace(",", "")
    elif "," in cleaned:
        normalized = cleaned.replace(".", "").replace(",", ".")
    else:
        normalized = cleaned

    try:
        decimal_amount = Decimal(normalized)
    except InvalidOperation:
        return None

    cents = (decimal_amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(cents)


def format_amount(amount_cents: int, currency: str = DEFAULT_EXPENSE_CURRENCY) -> str:
    absolute_cents = abs(amount_cents)
    whole = absolute_cents // 100
    decimals = absolute_cents % 100
    whole_text = f"{whole:,}".replace(",", ".")
    sign = "-" if amount_cents < 0 else ""
    return f"{currency} {sign}{whole_text},{decimals:02d}"


def build_expense_line(
    expense_id: int,
    amount_cents: int,
    currency: str,
    payment_method: str,
    source: str,
    description: str,
    user_label: str,
    sync_status: str,
) -> str:
    return (
        f"- #{expense_id} | {format_amount(amount_cents, currency)} | {payment_method} | "
        f"{source} | {description} | {user_label} | {sync_status}"
    )


def sync_status_label(language: str, synced: bool) -> str:
    return t(language, "expenses.synced") if synced else t(language, "expenses.pending")


def fallback_sheet_detail(language: str, configured: bool, ready: bool) -> str:
    if not configured:
        return t(language, "expenses.sheet_not_configured")
    if not ready:
        return t(language, "expenses.sheet_not_ready")
    return t(language, "expenses.sheet_ready")


def expense_usage_example(language: str = DEFAULT_LANGUAGE) -> str:
    return t(
        language,
        "expenses.usage_example",
        example="/gasto 18500 | transferencia | caja del grupo | pizzas de la juntada",
    )
