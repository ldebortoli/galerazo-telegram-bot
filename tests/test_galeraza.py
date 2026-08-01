from __future__ import annotations

import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Barrier

from telegram import Chat, Message, Update, User
from telegram.ext import filters

from galerazo_bot.database import Database, GalerazaScore
from galerazo_bot.galeraza import build_galeraza_lines, build_galeraza_pages, render_galeraza_page
from galerazo_bot.telegram_bot import _bold_first_line_entities, _galeraza_game_date, _is_galeraza_candidate


STATUS_UPDATE_FIELDS = {
    "CHAT_BACKGROUND_SET": "chat_background_set",
    "CHAT_CREATED": "group_chat_created",
    "CHAT_OWNER_CHANGED": "chat_owner_changed",
    "CHAT_OWNER_LEFT": "chat_owner_left",
    "CHAT_SHARED": "chat_shared",
    "CHECKLIST_TASKS_ADDED": "checklist_tasks_added",
    "CHECKLIST_TASKS_DONE": "checklist_tasks_done",
    "CONNECTED_WEBSITE": "connected_website",
    "DELETE_CHAT_PHOTO": "delete_chat_photo",
    "DIRECT_MESSAGE_PRICE_CHANGED": "direct_message_price_changed",
    "FORUM_TOPIC_CLOSED": "forum_topic_closed",
    "FORUM_TOPIC_CREATED": "forum_topic_created",
    "FORUM_TOPIC_EDITED": "forum_topic_edited",
    "FORUM_TOPIC_REOPENED": "forum_topic_reopened",
    "GENERAL_FORUM_TOPIC_HIDDEN": "general_forum_topic_hidden",
    "GENERAL_FORUM_TOPIC_UNHIDDEN": "general_forum_topic_unhidden",
    "GIFT": "gift",
    "GIFT_UPGRADE_SENT": "gift_upgrade_sent",
    "GIVEAWAY_COMPLETED": "giveaway_completed",
    "GIVEAWAY_CREATED": "giveaway_created",
    "LEFT_CHAT_MEMBER": "left_chat_member",
    "MANAGED_BOT_CREATED": "managed_bot_created",
    "MESSAGE_AUTO_DELETE_TIMER_CHANGED": "message_auto_delete_timer_changed",
    "MIGRATE": "migrate_to_chat_id",
    "NEW_CHAT_MEMBERS": "new_chat_members",
    "NEW_CHAT_PHOTO": "new_chat_photo",
    "NEW_CHAT_TITLE": "new_chat_title",
    "PAID_MESSAGE_PRICE_CHANGED": "paid_message_price_changed",
    "PINNED_MESSAGE": "pinned_message",
    "POLL_OPTION_ADDED": "poll_option_added",
    "POLL_OPTION_DELETED": "poll_option_deleted",
    "PROXIMITY_ALERT_TRIGGERED": "proximity_alert_triggered",
    "REFUNDED_PAYMENT": "refunded_payment",
    "SUGGESTED_POST_APPROVAL_FAILED": "suggested_post_approval_failed",
    "SUGGESTED_POST_APPROVED": "suggested_post_approved",
    "SUGGESTED_POST_DECLINED": "suggested_post_declined",
    "SUGGESTED_POST_PAID": "suggested_post_paid",
    "SUGGESTED_POST_REFUNDED": "suggested_post_refunded",
    "UNIQUE_GIFT": "unique_gift",
    "USERS_SHARED": "users_shared",
    "VIDEO_CHAT_ENDED": "video_chat_ended",
    "VIDEO_CHAT_PARTICIPANTS_INVITED": "video_chat_participants_invited",
    "VIDEO_CHAT_SCHEDULED": "video_chat_scheduled",
    "VIDEO_CHAT_STARTED": "video_chat_started",
    "WEB_APP_DATA": "web_app_data",
    "WRITE_ACCESS_ALLOWED": "write_access_allowed",
}


class GalerazaRenderingTests(unittest.TestCase):
    def test_uses_display_names_and_never_mentions_usernames(self) -> None:
        scores = [
            GalerazaScore("1", "alias", "Nombre Visible", 3),
            GalerazaScore("2", "alias_sin_nombre", None, 2),
            GalerazaScore("3", None, None, 1),
        ]

        lines = build_galeraza_lines(scores, language="es")

        self.assertEqual(
            lines,
            [
                "1. Nombre Visible (1) => 3",
                "2. alias_sin_nombre (2) => 2",
                "3. Usuario (3) => 1",
            ],
        )
        self.assertNotIn("@", "\n".join(lines))

    def test_uses_competition_ranks_and_aligns_ties(self) -> None:
        scores = [
            GalerazaScore("1", None, "Galerazo", 9),
            GalerazaScore("2", None, "Jo", 8),
            GalerazaScore("3", None, "Van", 8),
            GalerazaScore("4", None, "Lil", 7),
        ]

        self.assertEqual(
            build_galeraza_lines(scores),
            [
                "1. Galerazo (1) => 9",
                "2. Jo (2) => 8",
                "   Van (3) => 8",
                "4. Lil (4) => 7",
            ],
        )

    def test_all_ties_and_empty_rankings(self) -> None:
        tied_scores = [
            GalerazaScore("1", None, "Galerazo", 9),
            GalerazaScore("2", None, "Jo", 9),
            GalerazaScore("3", None, "Van", 9),
        ]

        self.assertEqual(
            build_galeraza_lines(tied_scores),
            [
                "1. Galerazo (1) => 9",
                "   Jo (2) => 9",
                "   Van (3) => 9",
            ],
        )
        self.assertEqual(build_galeraza_lines([]), ["Nadie tiene Galerazas hasta ahora."])
        self.assertEqual(
            build_galeraza_lines([], language="en"),
            ["Nobody has any Galerazas yet."],
        )

    def test_repeats_a_shared_position_only_at_the_start_of_a_new_page(self) -> None:
        scores = [
            GalerazaScore("1", None, "A", 9),
            GalerazaScore("2", None, "B", 8),
            GalerazaScore("3", None, "C", 8),
        ]

        pages = build_galeraza_pages(scores, max_chars=45)

        self.assertEqual(pages[0], "Tabla de Galerazas\n\n1. A (1) => 9")
        self.assertEqual(pages[1], "Tabla de Galerazas\n\n2. B (2) => 8")
        self.assertEqual(pages[2], "Tabla de Galerazas\n\n2. C (3) => 8")

    def test_uses_bold_table_title_separated_from_ranking(self) -> None:
        page = render_galeraza_page(
            [GalerazaScore("1", None, "Nombre", 3)],
            page=1,
            language="es",
        )
        entities = _bold_first_line_entities(page.text)

        self.assertEqual(page.text, "Tabla de Galerazas\n\n1. Nombre (1) => 3")
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0].type, "bold")
        self.assertEqual(entities[0].offset, 0)
        self.assertEqual(entities[0].length, len("Tabla de Galerazas"))


class GalerazaAwardTests(unittest.TestCase):
    def _message(self, sent_at: datetime, user: User | None = None, **kwargs) -> Message:
        sender = user or User(id=1, first_name="User", is_bot=False)
        return Message(
            message_id=10,
            date=sent_at,
            chat=Chat(id=-1, type="group"),
            from_user=sender,
            **kwargs,
        )

    def test_telegram_timestamp_is_converted_to_argentina_date(self) -> None:
        before_midnight = self._message(
            datetime(2026, 7, 11, 2, 59, 59, tzinfo=timezone.utc),
            text="before",
        )
        at_midnight = self._message(
            datetime(2026, 7, 11, 3, 0, 0, tzinfo=timezone.utc),
            text="after",
        )

        self.assertEqual(_galeraza_game_date(before_midnight), "2026-07-10")
        self.assertEqual(_galeraza_game_date(at_midnight), "2026-07-11")

    def test_all_original_human_messages_are_candidates(self) -> None:
        sent_at = datetime(2026, 7, 11, 4, 0, tzinfo=timezone.utc)
        user = User(id=1, first_name="User", is_bot=False)
        message = self._message(sent_at, user, text="original")

        self.assertTrue(_is_galeraza_candidate(Update(1, message=message), message, user))
        self.assertFalse(
            _is_galeraza_candidate(Update(2, edited_message=message), message, user)
        )

        bot = User(id=2, first_name="Bot", is_bot=True)
        bot_message = self._message(sent_at, bot, text="bot")
        self.assertFalse(
            _is_galeraza_candidate(Update(3, message=bot_message), bot_message, bot)
        )

        service_message = self._message(sent_at, user, new_chat_members=(user,))
        service_update = Update(4, message=service_message)
        self.assertEqual(service_update.effective_user, user)
        self.assertTrue(
            _is_galeraza_candidate(
                service_update,
                service_message,
                user,
            )
        )

    def test_pin_add_and_leave_events_are_candidates(self) -> None:
        sent_at = datetime(2026, 7, 11, 4, 0, tzinfo=timezone.utc)
        actor = User(id=1, first_name="Actor", is_bot=False)
        other_user = User(id=2, first_name="Other", is_bot=False)
        pinned_message = self._message(sent_at, other_user, text="pinned")
        cases = {
            "pinned_message": pinned_message,
            "new_chat_members": (other_user,),
            "left_chat_member": other_user,
        }

        for update_id, (field, value) in enumerate(cases.items(), start=10):
            with self.subTest(field=field):
                message = self._message(sent_at, actor, **{field: value})
                update = Update(update_id, message=message)

                self.assertTrue(filters.StatusUpdate.ALL.check_update(update))
                self.assertEqual(update.effective_user, actor)
                self.assertTrue(_is_galeraza_candidate(update, message, actor))

    def test_every_ptb_status_update_with_human_sender_is_candidate(self) -> None:
        available_filters = {
            name
            for name in dir(filters.StatusUpdate)
            if name.isupper() and name != "ALL"
        }
        self.assertEqual(set(STATUS_UPDATE_FIELDS), available_filters)

        sent_at = datetime(2026, 7, 11, 4, 0, tzinfo=timezone.utc)
        user = User(id=1, first_name="User", is_bot=False)
        for update_id, (filter_name, field) in enumerate(
            STATUS_UPDATE_FIELDS.items(),
            start=100,
        ):
            with self.subTest(filter_name=filter_name):
                message = self._message(sent_at, user)
                # Each PTB status filter checks this Message slot for truthiness.
                object.__setattr__(message, field, True)
                update = Update(update_id, message=message)
                status_filter = getattr(filters.StatusUpdate, filter_name)

                self.assertTrue(status_filter.check_update(update))
                self.assertTrue(filters.StatusUpdate.ALL.check_update(update))
                self.assertEqual(update.effective_user, user)
                self.assertTrue(_is_galeraza_candidate(update, message, user))

    def test_winner_persists_telegram_message_date(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            db.register_chat("-1", "group", "Group")
            message_date = "2026-07-11T03:00:00+00:00"

            self.assertTrue(
                db.try_award_daily_galeraza(
                    "-1",
                    "2026-07-11",
                    "1",
                    "10",
                    message_date,
                )
            )
            with db._connect() as conn:
                row = conn.execute(
                    "SELECT message_date FROM galeraza_daily_winners"
                ).fetchone()

            self.assertEqual(row["message_date"], message_date)

    def test_concurrent_database_candidates_create_only_one_winner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            db.register_chat("-1", "group", "Group")
            barrier = Barrier(2)

            def attempt(user_id: str, message_id: str) -> bool:
                barrier.wait()
                return db.try_award_daily_galeraza(
                    "-1",
                    "2026-07-11",
                    user_id,
                    message_id,
                    "2026-07-11T03:00:00+00:00",
                )

            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(
                    executor.map(
                        lambda args: attempt(*args),
                        [("1", "10"), ("2", "11")],
                    )
                )

            self.assertEqual(results.count(True), 1)
            self.assertEqual(sum(score.points for score in db.get_galeraza_scores("-1")), 1)


if __name__ == "__main__":
    unittest.main()
