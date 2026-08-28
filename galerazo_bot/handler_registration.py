from __future__ import annotations

from collections.abc import Awaitable, Callable, Collection

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    PrefixHandler,
    filters,
)


class RefundedPaymentFilter(filters.MessageFilter):
    def filter(self, message) -> bool:
        return message.refunded_payment is not None


REFUNDED_PAYMENT = RefundedPaymentFilter()


def register_handlers(
    application: Application,
    *,
    command_names: Collection[str],
    command_prefixes: Collection[str],
    chat_migration_callback: Callable[..., Awaitable[None]],
    preprocess_message: Callable[..., Awaitable[None]],
    command_callback: Callable[..., Awaitable[None]],
    pagination_callback: Callable[..., Awaitable[None]],
    config_callback: Callable[..., Awaitable[None]],
    hisopo_callback: Callable[..., Awaitable[None]],
    power_callback: Callable[..., Awaitable[None]],
    chat_member_callback: Callable[..., Awaitable[None]],
    pre_checkout_callback: Callable[..., Awaitable[None]],
    successful_payment_callback: Callable[..., Awaitable[None]],
    refunded_payment_callback: Callable[..., Awaitable[None]],
    pagination_pattern: str,
    config_pattern: str,
    hisopo_pattern: str,
    power_pattern: str,
) -> None:
    """Wire Telegram's native handlers without interpreting ordinary text as commands."""
    application.add_handler(
        MessageHandler(filters.StatusUpdate.MIGRATE, chat_migration_callback),
        group=0,
    )
    application.add_handler(MessageHandler(filters.ALL, preprocess_message), group=0)

    for command_name in command_names:
        application.add_handler(CommandHandler(command_name, command_callback), group=1)

    application.add_handler(
        PrefixHandler(tuple(command_prefixes), tuple(command_names), command_callback),
        group=1,
    )
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_callback), group=1)
    application.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback),
        group=1,
    )
    application.add_handler(
        MessageHandler(REFUNDED_PAYMENT, refunded_payment_callback),
        group=1,
    )
    application.add_handler(CallbackQueryHandler(pagination_callback, pattern=pagination_pattern), group=1)
    application.add_handler(CallbackQueryHandler(config_callback, pattern=config_pattern), group=1)
    application.add_handler(CallbackQueryHandler(hisopo_callback, pattern=hisopo_pattern), group=1)
    application.add_handler(CallbackQueryHandler(power_callback, pattern=power_pattern), group=1)
    application.add_handler(ChatMemberHandler(chat_member_callback, ChatMemberHandler.MY_CHAT_MEMBER), group=1)
