from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from telegram import Update
from telegram.ext import BaseUpdateProcessor


class PerChatUpdateProcessor(BaseUpdateProcessor):
    def __init__(
        self,
        resolve_chat_id: Callable[[str], str],
        max_concurrent_updates: int = 256,
    ) -> None:
        super().__init__(max_concurrent_updates=max_concurrent_updates)
        self._resolve_chat_id = resolve_chat_id
        self._aliases: dict[str, str] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._chatless_lock = asyncio.Lock()

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        self._aliases.clear()
        self._locks.clear()

    async def do_process_update(self, update: object, coroutine: Awaitable[Any]) -> None:
        migration = self._migration_chat_ids(update)
        if migration is not None:
            old_chat_id, new_chat_id = migration
            old_key = self._canonical_chat_id(old_chat_id)
            new_key = self._canonical_chat_id(new_chat_id)
            self._aliases[old_chat_id] = new_key

            if old_key == new_key:
                async with self._lock_for(new_key):
                    await coroutine
                return

            # Claim the destination first so later supergroup updates wait for migration.
            async with self._lock_for(new_key):
                async with self._lock_for(old_key):
                    await coroutine
            return

        chat_id = self._effective_chat_id(update)
        if chat_id is None:
            async with self._chatless_lock:
                await coroutine
            return

        async with self._lock_for(self._canonical_chat_id(chat_id)):
            await coroutine

    def _canonical_chat_id(self, chat_id: str) -> str:
        current = chat_id
        seen: list[str] = []
        while current in self._aliases and self._aliases[current] != current:
            seen.append(current)
            current = self._aliases[current]

        if not seen and current not in self._aliases:
            resolved = str(self._resolve_chat_id(current))
            self._aliases[current] = resolved
            current = resolved

        for alias in seen:
            self._aliases[alias] = current
        return current

    def _lock_for(self, chat_id: str) -> asyncio.Lock:
        return self._locks.setdefault(chat_id, asyncio.Lock())

    @staticmethod
    def _effective_chat_id(update: object) -> str | None:
        if not isinstance(update, Update) or update.effective_chat is None:
            return None
        return str(update.effective_chat.id)

    @staticmethod
    def _migration_chat_ids(update: object) -> tuple[str, str] | None:
        if not isinstance(update, Update) or update.effective_message is None:
            return None

        message = update.effective_message
        if message.migrate_to_chat_id is not None:
            return str(message.chat.id), str(message.migrate_to_chat_id)
        if message.migrate_from_chat_id is not None:
            return str(message.migrate_from_chat_id), str(message.chat.id)
        return None
