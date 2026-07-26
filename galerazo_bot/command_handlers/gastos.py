from __future__ import annotations

from ..commands import Command
from ..database import Database
from ..expenses import (
    DEFAULT_EXPENSE_LIST_LIMIT,
    build_expense_line,
    expense_usage_example,
    parse_expense_command_args,
    sync_status_label,
)
from ..roles import CommandContext, UserLevel
from ..user_display import format_user


async def gasto(context: CommandContext, _db: Database) -> str:
    draft = parse_expense_command_args(context.args)
    if draft is None:
        return f"{context.t('expenses.usage')}\n{expense_usage_example(context.language)}"
    if context.submit_expense is None:
        return context.t("expenses.not_configured")

    result = await context.submit_expense(
        draft.currency,
        str(draft.amount_cents),
        draft.payment_method,
        draft.source,
        draft.description,
    )
    amount_text = context.t("expenses.amount_saved", amount=_format_amount(context, int(draft.amount_cents), draft.currency))
    if result.synced:
        return context.t("expenses.saved_synced", expense_id=result.expense_id, amount=amount_text)
    if not result.configured:
        return context.t("expenses.saved_local_only", expense_id=result.expense_id, amount=amount_text)
    return context.t("expenses.saved_pending", expense_id=result.expense_id, amount=amount_text)


def ultimosgastos(context: CommandContext, db: Database) -> str:
    expenses = db.list_recent_expenses(context.chat_id, limit=DEFAULT_EXPENSE_LIST_LIMIT)
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
                source=expense.source,
                description=expense.description,
                user_label=_expense_user_label(context, expense),
                sync_status=sync_status_label(context.language, expense.sheet_status == "synced"),
            )
        )
    return "\n".join(lines)


def estadogastos(context: CommandContext, db: Database) -> str:
    if context.get_expense_sheet_status is None:
        detail = context.t("expenses.sheet_not_configured")
        pending_count = db.count_pending_expenses(context.chat_id)
    else:
        status = context.get_expense_sheet_status()
        detail = status.detail or context.t("expenses.sheet_not_configured")
        pending_count = status.pending_count

    return "\n".join(
        [
            context.t("expenses.status_header"),
            f"- {detail}",
            context.t("expenses.pending_count", count=pending_count),
            expense_usage_example(context.language),
        ]
    )


async def sincronizargastos(context: CommandContext, db: Database) -> str:
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


def _expense_user_label(context: CommandContext, expense) -> str:
    return format_user(expense, context)


def _format_amount(context: CommandContext, amount_cents: int, currency: str) -> str:
    from ..expenses import format_amount

    return format_amount(amount_cents, currency)


COMMANDS = {
    "gasto": Command(
        "gasto",
        "registra un gasto",
        gasto,
        UserLevel.DEV,
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
