from __future__ import annotations

import asyncio
import unittest
from datetime import datetime, timezone

from telegram import Chat, Message, Update, User

from galerazo_bot.update_processor import PerChatUpdateProcessor


def _update(update_id: int, chat_id: int, **message_kwargs) -> Update:
    return Update(
        update_id,
        message=Message(
            message_id=update_id,
            date=datetime(2026, 7, 11, tzinfo=timezone.utc),
            chat=Chat(id=chat_id, type="group"),
            from_user=User(id=1, first_name="User", is_bot=False),
            **message_kwargs,
        ),
    )


class PerChatUpdateProcessorTests(unittest.IsolatedAsyncioTestCase):
    async def test_same_chat_updates_keep_arrival_order(self) -> None:
        processor = PerChatUpdateProcessor(lambda chat_id: chat_id)
        first_started = asyncio.Event()
        release_first = asyncio.Event()
        events: list[str] = []

        async def first() -> None:
            events.append("first-start")
            first_started.set()
            await release_first.wait()
            events.append("first-end")

        async def second() -> None:
            events.append("second")

        first_task = asyncio.create_task(processor.do_process_update(_update(1, -1), first()))
        await first_started.wait()
        second_task = asyncio.create_task(processor.do_process_update(_update(2, -1), second()))
        await asyncio.sleep(0)

        self.assertEqual(events, ["first-start"])
        release_first.set()
        await asyncio.gather(first_task, second_task)
        self.assertEqual(events, ["first-start", "first-end", "second"])

    async def test_different_chats_can_run_in_parallel(self) -> None:
        processor = PerChatUpdateProcessor(lambda chat_id: chat_id)
        first_started = asyncio.Event()
        release_first = asyncio.Event()
        second_started = asyncio.Event()

        async def first() -> None:
            first_started.set()
            await release_first.wait()

        async def second() -> None:
            second_started.set()

        first_task = asyncio.create_task(processor.do_process_update(_update(1, -1), first()))
        await first_started.wait()
        second_task = asyncio.create_task(processor.do_process_update(_update(2, -2), second()))
        await asyncio.wait_for(second_started.wait(), timeout=1)

        release_first.set()
        await asyncio.gather(first_task, second_task)

    async def test_migration_preserves_order_across_old_and_new_chat_ids(self) -> None:
        processor = PerChatUpdateProcessor(lambda chat_id: chat_id)
        release_old = asyncio.Event()
        old_started = asyncio.Event()
        events: list[str] = []

        async def old_message() -> None:
            events.append("old-start")
            old_started.set()
            await release_old.wait()
            events.append("old-end")

        async def migration() -> None:
            events.append("migration")

        async def new_message() -> None:
            events.append("new")

        old_task = asyncio.create_task(
            processor.do_process_update(_update(1, -10), old_message())
        )
        await old_started.wait()
        migration_task = asyncio.create_task(
            processor.do_process_update(
                _update(2, -10, migrate_to_chat_id=-10010),
                migration(),
            )
        )
        await asyncio.sleep(0)
        new_task = asyncio.create_task(
            processor.do_process_update(_update(3, -10010), new_message())
        )
        await asyncio.sleep(0)

        self.assertEqual(events, ["old-start"])
        release_old.set()
        await asyncio.gather(old_task, migration_task, new_task)
        self.assertEqual(events, ["old-start", "old-end", "migration", "new"])


if __name__ == "__main__":
    unittest.main()
