from __future__ import annotations

import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from ..command_model import Command
from ..database import Database
from ..expenses import (
    DEFAULT_EXPENSE_LIST_LIMIT,
    build_expense_line,
    expense_help_text,
    expense_usage_example,
    parse_card_statement_command_args,
    parse_closing_date,
    parse_expense_command_args,
    sync_status_label,
)
from ..roles import CommandContext, UserLevel
from ..user_display import format_user


ARGENTINA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


async def gasto(context: CommandContext, _db: Database) -> str:
    denied = _expense_permission_error(context)
    if denied:
        return denied
    draft = parse_expense_command_args(
        context.args,
        default_author=_default_author(context),
        today=_today(),
    )
    if draft is None:
        return f"Uso inválido. {expense_usage_example()}\nUsá /ayudagastos para ver formatos y alias."
    return await _submit(context, draft)


async def pagoresumen(context: CommandContext, _db: Database) -> str:
    denied = _expense_permission_error(context)
    if denied:
        return denied
    draft = parse_card_statement_command_args(
        context.args,
        default_author=_default_author(context),
        today=_today(),
    )
    if draft is None:
        return (
            "Uso: /pagoresumen monto | forma de pago | descripción. "
            "Podés agregar autor, fecha y @cotización antes de la descripción."
        )
    return await _submit(context, draft)


async def _submit(context: CommandContext, draft) -> str:
    if context.submit_expense is None:
        return context.t("expenses.not_configured")
    result = await context.submit_expense(draft)
    amount_text = _format_amount(int(draft.amount_cents), draft.currency)
    if result.synced:
        return f"Gasto #{result.expense_id} registrado y sincronizado ({amount_text})."
    if result.error == "cashflow_month_not_open":
        return (
            f"Gasto #{result.expense_id} guardado como pendiente ({amount_text}). "
            "El mes todavía no está abierto en la hoja anual; un pago de resumen nunca "
            "lo abre. Se reintentará cuando exista el primer gasto común del mes."
        )
    if result.error == "historical_rate_required":
        return (
            "Para una fecha anterior a hoy indicá la cotización de ese momento con "
            "@valor, por ejemplo @1559,40. No guardé el gasto."
        )
    if result.error == "exchange_rate_unavailable":
        return "No pude obtener la venta USDT de Binance en CriptoYa. No guardé el gasto."
    if not result.configured:
        return context.t(
            "expenses.saved_local_only",
            expense_id=result.expense_id,
            amount=amount_text,
        )
    return context.t(
        "expenses.saved_pending",
        expense_id=result.expense_id,
        amount=amount_text,
    )


async def cierre(context: CommandContext, _db: Database) -> str:
    denied = _expense_permission_error(context)
    if denied:
        return denied
    closing_date = parse_closing_date(context.args, _today())
    if closing_date is None:
        return "Uso: /cierre dd/mm/aaaa"
    if context.add_card_closing is None:
        return context.t("expenses.sheet_not_configured")
    result = await context.add_card_closing(closing_date)
    if result.duplicate:
        return f"El cierre {closing_date:%d/%m/%Y} ya estaba cargado."
    if result.added:
        return f"Cierre {closing_date:%d/%m/%Y} agregado en la fila {result.row_number}."
    if not result.configured:
        return context.t("expenses.sheet_not_configured")
    return f"No pude agregar el cierre: {result.error or 'error desconocido'}."


def ayudagastos(context: CommandContext, _db: Database) -> str:
    denied = _expense_permission_error(context)
    return denied or expense_help_text()


def ultimosgastos(context: CommandContext, db: Database) -> str:
    denied = _expense_permission_error(context)
    if denied:
        return denied
    expenses = db.list_recent_expenses(None, limit=DEFAULT_EXPENSE_LIST_LIMIT)
    if not expenses:
        return context.t("expenses.empty")

    lines = [context.t("expenses.list_header")]
    for expense in expenses:
        lines.append(
            build_expense_line(
                expense_id=expense.expense_id,
                amount_cents=expense.amount_cents,
                currency=expense.currency,
                payment_method=expense.payment_method,
                source=expense.category,
                description=expense.description,
                user_label=_expense_user_label(context, expense),
                sync_status=sync_status_label(context.language, expense.sheet_status == "synced"),
            )
        )
    return "\n".join(lines)


def estadogastos(context: CommandContext, db: Database) -> str:
    denied = _expense_permission_error(context)
    if denied:
        return denied
    if context.get_expense_sheet_status is None:
        detail = context.t("expenses.sheet_not_configured")
        pending_count = db.count_pending_expenses(None)
    else:
        status = context.get_expense_sheet_status()
        detail = status.detail or context.t("expenses.sheet_not_configured")
        pending_count = status.pending_count

    return "\n".join(
        [
            context.t("expenses.status_header"),
            f"- {detail}",
            context.t("expenses.pending_count", count=pending_count),
            "Cotización: CriptoYa, USDT, fila Binance, columna Vendés a (no Binance P2P).",
            "Usá /ayudagastos para ver el funcionamiento completo.",
        ]
    )


async def sincronizargastos(context: CommandContext, _db: Database) -> str:
    denied = _expense_permission_error(context)
    if denied:
        return denied
    if context.sync_expenses is None:
        return context.t("expenses.sheet_not_configured")

    result = await context.sync_expenses()
    if not result.configured:
        return context.t("expenses.sheet_not_configured")
    if result.failed_count == 0:
        return context.t("expenses.sync_done", synced=result.synced_count, failed=result.failed_count)
    return context.t(
        "expenses.sync_partial",
        synced=result.synced_count,
        failed=result.failed_count,
    )


def _expense_permission_error(context: CommandContext) -> str | None:
    if context.chat_type == "private" and context.sender_id in context.expense_user_ids:
        return None
    return "Este comando de gastos solo está disponible por privado para Lucas y Jo."


def _default_author(context: CommandContext) -> str:
    return "Lucas" if context.owner_user_id == context.sender_id else "Jo"


def _today():
    return datetime.now(ARGENTINA_TZ).date()


def _expense_user_label(context: CommandContext, expense) -> str:
    return format_user(expense, context)


def _format_amount(amount_cents: int, currency: str) -> str:
    from ..expenses import format_amount

    return format_amount(amount_cents, currency)


def migrate_chat_data(conn: sqlite3.Connection, old_chat_id: str, new_chat_id: str) -> None:
    conn.execute("UPDATE expenses SET chat_id = ? WHERE chat_id = ?", (new_chat_id, old_chat_id))


COMMANDS = {
    "gasto": Command("gasto", "registra un gasto", gasto, UserLevel.DEV),
    "pagoresumen": Command(
        "pagoresumen",
        "registra el pago de un resumen de tarjeta",
        pagoresumen,
        UserLevel.DEV,
    ),
    "cierre": Command(
        "cierre",
        "agrega una fecha de cierre de tarjeta",
        cierre,
        UserLevel.DEV,
    ),
    "ayudagastos": Command(
        "ayudagastos",
        "explica cómo registrar y sincronizar gastos",
        ayudagastos,
        UserLevel.DEV,
        list_response=True,
    ),
    "ultimosgastos": Command(
        "ultimosgastos",
        "muestra los ultimos gastos",
        ultimosgastos,
        UserLevel.DEV,
        list_response=True,
    ),
    "estadogastos": Command(
        "estadogastos",
        "muestra el estado del sistema de gastos",
        estadogastos,
        UserLevel.DEV,
    ),
    "sincronizargastos": Command(
        "sincronizargastos",
        "sincroniza gastos pendientes con Google Sheets",
        sincronizargastos,
        UserLevel.DEV,
    ),
}
