from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import StrEnum

from .i18n import DEFAULT_LANGUAGE, t


DEFAULT_EXPENSE_CURRENCY = "ARS"
DEFAULT_EXPENSE_LIST_LIMIT = 20
CARD_STATEMENT_CATEGORY = "Pago resumen tarjetas"


class ExpenseMovement(StrEnum):
    PURCHASE = "purchase"
    CARD_STATEMENT = "card_statement"


@dataclass(frozen=True)
class PaymentMethod:
    label: str
    aliases: tuple[str, ...]
    deferred: bool = False


PAYMENT_METHODS = (
    PaymentMethod("Efectivo", ("ef", "efe", "efectivo")),
    PaymentMethod("Mercado Pago Jo", ("mpj", "mercado pago jo")),
    PaymentMethod("Mercado Pago Lucas", ("mpl", "mercado pago lucas")),
    PaymentMethod("Tarj Débito Galicia Jo", ("tdgj", "debito galicia jo", "tarj debito galicia jo")),
    PaymentMethod("Tarj Débito Galicia Lucas", ("tdgl", "debito galicia lucas", "tarj debito galicia lucas")),
    PaymentMethod("Tarj Débito BBVA Jo", ("tdbj", "debito bbva jo", "tarj debito bbva jo")),
    PaymentMethod("Saldo Galicia Jo", ("sgj", "saldo galicia jo")),
    PaymentMethod("Saldo Galicia Lucas", ("sgl", "saldo galicia lucas")),
    PaymentMethod("Saldo BBVA Jo", ("sbj", "saldo bbva jo")),
    PaymentMethod("Cuenta DNI Lucas", ("cdnl", "cdn", "cuenta dni lucas")),
    PaymentMethod("BUEPP Jo", ("bueppj", "buepp jo", "buepp joblep")),
    PaymentMethod("BUEPP Lucas", ("bueppl", "buepp lucas")),
    PaymentMethod("Personal Pay Lucas", ("ppl", "personal pay lucas")),
    PaymentMethod("TAP Jo", ("tapj", "tap jo")),
    PaymentMethod("TAP Lucas", ("tapl", "tap lucas")),
    PaymentMethod("Tarj PAYO USD Jo", ("payoj", "payo jo", "tarj payo usd jo")),
    PaymentMethod("Tarj PAYO USD Lucas", ("payol", "payo lucas", "tarj payo usd lucas")),
    PaymentMethod("Tarj VISA Galicia Jo", ("vgj", "visa galicia jo", "tarj visa galicia jo"), True),
    PaymentMethod("Tarj VISA Galicia Lucas", ("vgl", "visa galicia lucas", "tarj visa galicia lucas"), True),
    PaymentMethod("Tarj MASTER Galicia Jo", ("mgj", "master galicia jo", "tarj master galicia jo"), True),
    PaymentMethod("Tarj MASTER Galicia Lucas", ("mgl", "master galicia lucas", "tarj master galicia lucas"), True),
    PaymentMethod("Tarj Crédito Mercado Pago", ("cmp", "mpc", "credito mercado pago", "tarj credito mercado pago", "tarj mp lucas", "tarj mercado pago"), True),
    PaymentMethod("Tarj Grabrfi", ("grabrfi", "tarj grabrfi"), True),
)


CATEGORIES = (
    "Vanzazo",
    "Viajes",
    "Otros impuestos",
    "Regalos",
    "Celular",
    "Panadería",
    "Música",
    "Ferretería",
    "Salidas",
    "Comics",
    "Obra Social",
    "Extra Lucas",
    "Verdulería",
    "Librería",
    "Marroquinería",
    "Arreglos Hogar",
    "Ropa",
    "Transporte",
    "Extra Jo",
    "Carnicería",
    "Dulcería",
    "Fábrica de Pastas",
    "Impuestos y servicios Hogar",
    "Cosas para el hogar",
    "Supermercado",
    "Banco",
    "Fiambrería",
    "Casa de limpieza",
    "Dietética",
    "Farmacia",
    "Otros",
)


CATEGORY_ALIASES = {
    "vanz": "Vanzazo",
    "via": "Viajes",
    "imp": "Otros impuestos",
    "reg": "Regalos",
    "cel": "Celular",
    "pan": "Panadería",
    "mus": "Música",
    "fer": "Ferretería",
    "sal": "Salidas",
    "comic": "Comics",
    "os": "Obra Social",
    "elu": "Extra Lucas",
    "verd": "Verdulería",
    "lib": "Librería",
    "marroq": "Marroquinería",
    "hogar": "Arreglos Hogar",
    "ropa": "Ropa",
    "trans": "Transporte",
    "ejo": "Extra Jo",
    "carn": "Carnicería",
    "dul": "Dulcería",
    "pastas": "Fábrica de Pastas",
    "serv": "Impuestos y servicios Hogar",
    "cosash": "Cosas para el hogar",
    "sup": "Supermercado",
    "banco": "Banco",
    "fiam": "Fiambrería",
    "limp": "Casa de limpieza",
    "diet": "Dietética",
    "farm": "Farmacia",
    "otro": "Otros",
}


AUTHOR_ALIASES = {
    "l": "Lucas",
    "lucas": "Lucas",
    "j": "Jo",
    "jo": "Jo",
    "a": "Ambos",
    "ambos": "Ambos",
}


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.strip().casefold())
    return " ".join("".join(char for char in decomposed if not unicodedata.combining(char)).split())


_PAYMENT_BY_ALIAS = {
    _normalized(alias): method
    for method in PAYMENT_METHODS
    for alias in (*method.aliases, method.label)
}
_CATEGORY_BY_ALIAS = {
    **{_normalized(category): category for category in CATEGORIES},
    **{_normalized(alias): category for alias, category in CATEGORY_ALIASES.items()},
}


@dataclass(frozen=True)
class ExpenseDraft:
    amount_cents: int
    currency: str
    payment_method: str
    category: str
    author: str
    description: str
    occurred_on: date
    installments: int
    movement_type: ExpenseMovement
    include_cashflow: bool
    opens_cashflow_month: bool
    usd_rate_override: Decimal | None = None


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


@dataclass(frozen=True)
class CardClosingResult:
    configured: bool
    added: bool
    duplicate: bool = False
    row_number: int | None = None
    error: str | None = None


def resolve_payment_method(raw: str) -> PaymentMethod | None:
    return _PAYMENT_BY_ALIAS.get(_normalized(raw))


def resolve_category(raw: str) -> str | None:
    return _CATEGORY_BY_ALIAS.get(_normalized(raw))


def parse_expense_command_args(
    raw_args: str,
    default_author: str = "Lucas",
    today: date | None = None,
) -> ExpenseDraft | None:
    parts = [part.strip() for part in raw_args.split("|")]
    if len(parts) < 4 or any(not part for part in parts):
        return None

    amount = _parse_amount_token(parts[0])
    category = resolve_category(parts[1])
    if amount is None or category is None:
        return None

    amount_cents, currency = amount
    parsed = _parse_modifiers(parts[2:-1], default_author, today)
    if parsed is None:
        return None
    method, author, occurred_on, installments, usd_rate = parsed

    if currency == "USD":
        if installments not in (None, 1) or usd_rate is not None:
            return None
        installments = 1
    elif method.deferred:
        if installments is None:
            installments = 1
        if installments < 1:
            return None
    else:
        if installments not in (None, 0):
            return None
        installments = 0

    include_cashflow = not method.deferred
    return ExpenseDraft(
        amount_cents=amount_cents,
        currency=currency,
        payment_method=method.label,
        category=category,
        author=author,
        description=parts[-1],
        occurred_on=occurred_on,
        installments=installments,
        movement_type=ExpenseMovement.PURCHASE,
        include_cashflow=include_cashflow,
        opens_cashflow_month=include_cashflow,
        usd_rate_override=usd_rate,
    )


def parse_card_statement_command_args(
    raw_args: str,
    default_author: str = "Lucas",
    today: date | None = None,
) -> ExpenseDraft | None:
    parts = [part.strip() for part in raw_args.split("|")]
    if len(parts) < 3 or any(not part for part in parts):
        return None

    amount = _parse_amount_token(parts[0])
    if amount is None:
        return None
    amount_cents, currency = amount
    parsed = _parse_modifiers(parts[1:-1], default_author, today, allow_installments=False)
    if parsed is None:
        return None
    method, author, occurred_on, installments, usd_rate = parsed
    if installments is not None or method.deferred or (currency == "USD" and usd_rate is not None):
        return None

    return ExpenseDraft(
        amount_cents=amount_cents,
        currency=currency,
        payment_method=method.label,
        category=CARD_STATEMENT_CATEGORY,
        author=author,
        description=parts[-1],
        occurred_on=occurred_on,
        installments=0,
        movement_type=ExpenseMovement.CARD_STATEMENT,
        include_cashflow=True,
        opens_cashflow_month=False,
        usd_rate_override=usd_rate,
    )


def _parse_modifiers(
    raw_modifiers: list[str],
    default_author: str,
    today: date | None,
    *,
    allow_installments: bool = True,
) -> tuple[PaymentMethod, str, date, int | None, Decimal | None] | None:
    method = None
    author = default_author
    occurred_on = today or date.today()
    installments = None
    usd_rate = None
    author_seen = False
    date_seen = False

    for modifier in raw_modifiers:
        normalized = _normalized(modifier)
        candidate_method = resolve_payment_method(modifier)
        candidate_author = AUTHOR_ALIASES.get(normalized)
        candidate_date = _parse_date(modifier, occurred_on.year)
        candidate_installments = _parse_installments(modifier) if allow_installments else None
        candidate_rate = _parse_rate(modifier)

        if candidate_method is not None and method is None:
            method = candidate_method
        elif candidate_author is not None and not author_seen:
            author = candidate_author
            author_seen = True
        elif candidate_date is not None and not date_seen:
            occurred_on = candidate_date
            date_seen = True
        elif candidate_installments is not None and installments is None:
            installments = candidate_installments
        elif candidate_rate is not None and usd_rate is None:
            usd_rate = candidate_rate
        else:
            return None

    if method is None:
        return None
    return method, author, occurred_on, installments, usd_rate


def _parse_amount_token(raw_amount: str) -> tuple[int, str] | None:
    normalized = raw_amount.strip()
    currency = "USD" if normalized.casefold().endswith("usd") else "ARS"
    if currency == "USD":
        normalized = normalized[:-3].strip()
    amount_cents = parse_amount_to_cents(normalized)
    if amount_cents is None or amount_cents <= 0:
        return None
    return amount_cents, currency


def _parse_installments(raw: str) -> int | None:
    match = re.fullmatch(r"(\d+)\s*c?", raw.strip().casefold())
    return int(match.group(1)) if match is not None else None


def _parse_rate(raw: str) -> Decimal | None:
    stripped = raw.strip()
    if not stripped.startswith("@"):
        return None
    cents = parse_amount_to_cents(stripped[1:])
    if cents is None or cents <= 0:
        return None
    return Decimal(cents) / Decimal(100)


def _parse_date(raw: str, default_year: int) -> date | None:
    stripped = raw.strip()
    for pattern in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(stripped, pattern).date()
        except ValueError:
            pass
    for pattern in ("%d/%m", "%d-%m"):
        try:
            separator = "/" if "/" in stripped else "-"
            return datetime.strptime(
                f"{stripped}{separator}{default_year}",
                f"{pattern}{separator}%Y",
            ).date()
        except ValueError:
            pass
    return None


def parse_closing_date(raw: str, today: date | None = None) -> date | None:
    return _parse_date(raw, (today or date.today()).year)


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
    del language
    return "Ejemplo: /gasto 18500 | sal | mpl | pizzas de la juntada"


def expense_help_text() -> str:
    category_aliases = ", ".join(
        f"{alias}={category}" for alias, category in CATEGORY_ALIASES.items()
    )
    payment_aliases = ", ".join(
        f"{method.aliases[0]}={method.label}" for method in PAYMENT_METHODS
    )
    return (
        "Gastos funciona solamente por privado para Lucas y Jo.\n\n"
        "Compra inmediata (efectivo, débito, saldo o billetera): se anota en "
        "Gastos y compras y también en Gastos del año.\n"
        "Compra con tarjeta de crédito: se anota solo en Gastos y compras. Una carga "
        "atrasada de tarjeta nunca abre un mes nuevo.\n"
        "Pago de resumen: usá /pagoresumen; se anota solo como salida real en Gastos "
        "del año y tampoco abre un mes que todavía no exista.\n"
        "Las altas siempre continúan después de la última fila usada: nunca reutilizan "
        "huecos ni pisan una fila existente. Si aparece una colisión, el gasto queda "
        "pendiente.\n\n"
        "Formatos:\n"
        "/gasto monto | categoría | forma de pago | descripción\n"
        "/gasto monto | categoría | autor | forma de pago | cuotas | descripción\n"
        "/pagoresumen monto | forma de pago | descripción\n"
        "/cierre dd/mm/aaaa\n\n"
        "Opcionales antes de la descripción: l, j o a para el autor; 3c para cuotas; "
        "dd/mm/aaaa para otra fecha; @1559,40 para una cotización histórica. Los gastos "
        "en USD se escriben como 17.22usd, siempre son de un pago y no llevan cotización.\n\n"
        f"Categorías: {category_aliases}.\n\n"
        f"Formas de pago: {payment_aliases}.\n\n"
        "Para una fecha anterior a hoy tenés que indicar @cotización. Si CriptoYa no "
        "responde, el bot no inventa el valor. /sincronizargastos reintenta lo pendiente."
    )
