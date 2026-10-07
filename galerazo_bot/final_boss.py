"""Transactional, restart-safe rules for the collaborative Final Boss."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta

from .database import Database, HisopoSchedule, _increment_hisopo_collection, _insert_hisopo_schedule_below_daily_cap


PHASE_TWO_PRESSES = 1000
BUTTON_COUNT = 20
MAX_USER_BUTTONS = 5
MIN_PRESS_INTERVAL = timedelta(milliseconds=100)
PHASE_DURATIONS = {2: timedelta(minutes=30), 3: timedelta(minutes=30), 4: timedelta(minutes=10)}


@dataclass(frozen=True)
class BossState:
    chat_id: str
    message_id: str
    phase: int
    status: str
    expires_at: str
    required_helpers: int
    safe_slot: int
    phase1_users: tuple[str, ...]
    phase2_counts: tuple[tuple[str, int], ...]
    phase3_slots: tuple[tuple[int, str], ...]
    final_user_id: str | None
    reveal_user_id: str | None
    reason: str | None
    offender_user_id: str | None
    awards: tuple[tuple[str, int], ...]
    announcement_message_id: str | None
    announcement_complete: bool = False

    @property
    def phase2_total(self) -> int:
        return sum(count for _, count in self.phase2_counts)

    @property
    def phase3_count(self) -> int:
        return len(self.phase3_slots)

    @property
    def participant_user_ids(self) -> tuple[str, ...]:
        users = set(self.phase1_users)
        users.update(user_id for user_id, _ in self.phase2_counts)
        users.update(user_id for _, user_id in self.phase3_slots)
        if self.final_user_id is not None:
            users.add(self.final_user_id)
        return tuple(sorted(users))


@dataclass(frozen=True)
class BossActionResult:
    status: str
    state: BossState | None
    schedule: HisopoSchedule | None = None

    @property
    def awards(self) -> tuple[tuple[str, int], ...]:
        return self.state.awards if self.state is not None else ()


def initialize_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS final_boss_states (
            chat_id TEXT NOT NULL, message_id TEXT NOT NULL,
            phase INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'active',
            safe_slot INTEGER NOT NULL CHECK (safe_slot BETWEEN 0 AND 19),
            final_user_id TEXT, reveal_user_id TEXT, reason TEXT, offender_user_id TEXT,
            awards_json TEXT NOT NULL DEFAULT '[]', announcement_message_id TEXT,
            announcement_complete INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (chat_id, message_id),
            FOREIGN KEY (chat_id, message_id) REFERENCES hisopo_spawns (chat_id, message_id)
        )"""
    )
    if "announcement_complete" not in {row["name"] for row in conn.execute("PRAGMA table_info(final_boss_states)")}:
        conn.execute("ALTER TABLE final_boss_states ADD COLUMN announcement_complete INTEGER NOT NULL DEFAULT 0")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS final_boss_events (
            chat_id TEXT NOT NULL, message_id TEXT NOT NULL,
            callback_query_id TEXT NOT NULL, user_id TEXT NOT NULL,
            phase INTEGER NOT NULL, slot INTEGER, pressed_at TEXT NOT NULL,
            accepted INTEGER NOT NULL,
            PRIMARY KEY (chat_id, callback_query_id),
            FOREIGN KEY (chat_id, message_id) REFERENCES final_boss_states (chat_id, message_id)
        )"""
    )
    conn.execute(
        """CREATE INDEX IF NOT EXISTS idx_final_boss_events_spawn
        ON final_boss_events (chat_id, message_id, accepted, phase, user_id)"""
    )


def migrate_chat_data(conn: sqlite3.Connection, old_chat_id: str, new_chat_id: str) -> None:
    for table in ("final_boss_states", "final_boss_events"):
        conn.execute(
            f"""UPDATE OR IGNORE {table} SET chat_id = ? WHERE chat_id = ? AND EXISTS (
            SELECT 1 FROM hisopo_spawns old JOIN hisopo_spawns new
            ON new.chat_id = ? AND new.message_id = old.message_id
            AND new.hisopo_type = old.hisopo_type AND new.spawned_at = old.spawned_at
            WHERE old.chat_id = ? AND old.message_id = {table}.message_id)""",
            (new_chat_id, old_chat_id, new_chat_id, old_chat_id),
        )
        conn.execute(f"DELETE FROM {table} WHERE chat_id = ?", (old_chat_id,))


def _read_state(conn: sqlite3.Connection, chat_id: str, message_id: str) -> BossState | None:
    row = conn.execute(
        """SELECT b.*, s.expires_at, s.required_helpers
        FROM final_boss_states b JOIN hisopo_spawns s USING (chat_id, message_id)
        WHERE b.chat_id = ? AND b.message_id = ?""", (chat_id, message_id)
    ).fetchone()
    if row is None:
        return None
    events = conn.execute(
        """SELECT user_id, phase, slot FROM final_boss_events
        WHERE chat_id = ? AND message_id = ? AND accepted = 1
        ORDER BY pressed_at, callback_query_id""", (chat_id, message_id)
    ).fetchall()
    phase1: list[str] = []
    phase2: dict[str, int] = {}
    phase3: list[tuple[int, str]] = []
    for event in events:
        user_id = str(event["user_id"])
        if event["phase"] == 1:
            phase1.append(user_id)
        elif event["phase"] == 2:
            phase2[user_id] = phase2.get(user_id, 0) + 1
        elif event["phase"] == 3:
            phase3.append((int(event["slot"]), user_id))
    return BossState(
        chat_id=chat_id, message_id=message_id, phase=int(row["phase"]), status=row["status"],
        expires_at=row["expires_at"], required_helpers=int(row["required_helpers"]),
        safe_slot=int(row["safe_slot"]), phase1_users=tuple(phase1),
        phase2_counts=tuple(sorted(phase2.items())), phase3_slots=tuple(sorted(phase3)),
        final_user_id=row["final_user_id"], reveal_user_id=row["reveal_user_id"],
        reason=row["reason"], offender_user_id=row["offender_user_id"],
        awards=tuple((str(user), int(points)) for user, points in json.loads(row["awards_json"])),
        announcement_message_id=row["announcement_message_id"],
        announcement_complete=bool(row["announcement_complete"]),
    )


class FinalBossStore:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(self, chat_id: str, message_id: str, now: datetime, safe_slot: int) -> BossState:
        if not 0 <= safe_slot < BUTTON_COUNT:
            raise ValueError("The Final Boss safe slot must be between 0 and 19.")
        chat_id = self.db.resolve_chat_id(chat_id)
        with self.db._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            spawn = conn.execute(
                "SELECT hisopo_type FROM hisopo_spawns WHERE chat_id = ? AND message_id = ?",
                (chat_id, message_id),
            ).fetchone()
            if spawn is None or spawn["hisopo_type"] != "final_boss":
                raise ValueError("A saved Final Boss spawn is required.")
            conn.execute(
                "INSERT OR IGNORE INTO final_boss_states (chat_id, message_id, safe_slot) VALUES (?, ?, ?)",
                (chat_id, message_id, safe_slot),
            )
            conn.execute(
                "UPDATE hisopo_spawns SET message_cleanup_status = 'preserved' WHERE chat_id = ? AND message_id = ?",
                (chat_id, message_id),
            )
            return _read_state(conn, chat_id, message_id)

    def get(self, chat_id: str, message_id: str) -> BossState | None:
        chat_id = self.db.resolve_chat_id(chat_id)
        with self.db._connect() as conn:
            return _read_state(conn, chat_id, message_id)

    def contribute(
        self, chat_id: str, message_id: str, user_id: str, callback_query_id: str,
        phase: int, now: datetime, slot: int | None = None,
        next_scheduled_for: datetime | None = None,
    ) -> BossActionResult:
        chat_id = self.db.resolve_chat_id(chat_id)
        with self.db._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            state = _read_state(conn, chat_id, message_id)
            if state is None:
                return BossActionResult("missing", None)
            if phase not in (1, 2, 3, 4) or not callback_query_id:
                return BossActionResult("invalid", state)
            if (phase < 3 and slot is not None) or (phase >= 3 and (slot is None or not 0 <= slot < BUTTON_COUNT)):
                return BossActionResult("invalid", state)
            duplicate = conn.execute(
                "SELECT 1 FROM final_boss_events WHERE chat_id = ? AND callback_query_id = ?",
                (chat_id, callback_query_id),
            ).fetchone()
            if duplicate is not None:
                return BossActionResult("duplicate", state)
            if state.status != "active":
                return BossActionResult("finished", state)
            if now >= datetime.fromisoformat(state.expires_at):
                return self._finish(conn, state, now, "abandoned" if state.phase == 1 and not state.phase1_users else "timeout")
            conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            if phase != state.phase:
                self._event(conn, state, user_id, callback_query_id, phase, slot, now, False)
                return BossActionResult("stale", state)
            if phase == 1 and user_id in state.phase1_users:
                self._event(conn, state, user_id, callback_query_id, phase, slot, now, False)
                return BossActionResult("already_joined", state)
            if phase == 2:
                last = conn.execute(
                    """SELECT pressed_at FROM final_boss_events
                    WHERE chat_id = ? AND message_id = ? AND user_id = ? AND phase = 2 AND accepted = 1
                    ORDER BY pressed_at DESC LIMIT 1""", (chat_id, message_id, user_id)
                ).fetchone()
                if last is not None and now - datetime.fromisoformat(last["pressed_at"]) < MIN_PRESS_INTERVAL:
                    self._event(conn, state, user_id, callback_query_id, phase, slot, now, False)
                    return BossActionResult("throttled", state)
            if phase == 3:
                reason = None
                if slot in dict(state.phase3_slots):
                    reason = "duplicate_slot"
                elif sum(owner == user_id for _, owner in state.phase3_slots) >= MAX_USER_BUTTONS:
                    reason = "user_limit"
                if reason is not None:
                    self._event(conn, state, user_id, callback_query_id, phase, slot, now, False)
                    return self._finish(conn, state, now, reason, user_id)
            if phase == 4 and slot != state.safe_slot:
                self._event(conn, state, user_id, callback_query_id, phase, slot, now, False)
                return self._finish(conn, state, now, "exploded", user_id)
            self._event(conn, state, user_id, callback_query_id, phase, slot, now, True)
            conn.execute(
                """UPDATE final_boss_states SET reveal_user_id = ?
                WHERE chat_id = ? AND message_id = ? AND reveal_user_id IS NULL
                AND EXISTS (SELECT 1 FROM hisopo_spawns WHERE chat_id = ? AND message_id = ? AND appearance_type = 'mystery')""",
                (user_id, chat_id, message_id, chat_id, message_id),
            )
            conn.execute(
                "UPDATE hisopo_spawns SET appearance_type = 'final_boss' WHERE chat_id = ? AND message_id = ?",
                (chat_id, message_id),
            )
            if phase == 4:
                conn.execute(
                    "UPDATE final_boss_states SET final_user_id = ? WHERE chat_id = ? AND message_id = ?",
                    (user_id, chat_id, message_id),
                )
                return self._finish(conn, _read_state(conn, chat_id, message_id), now, "won", next_scheduled_for=next_scheduled_for)
            state = _read_state(conn, chat_id, message_id)
            completed = (
                (phase == 1 and len(state.phase1_users) >= state.required_helpers)
                or (phase == 2 and state.phase2_total >= PHASE_TWO_PRESSES)
                or (phase == 3 and state.phase3_count == BUTTON_COUNT)
            )
            if completed:
                conn.execute("UPDATE final_boss_states SET phase = ? WHERE chat_id = ? AND message_id = ?", (phase + 1, chat_id, message_id))
                conn.execute(
                    "UPDATE hisopo_spawns SET expires_at = ? WHERE chat_id = ? AND message_id = ?",
                    ((now + PHASE_DURATIONS[phase + 1]).isoformat(), chat_id, message_id),
                )
                return BossActionResult("advanced", _read_state(conn, chat_id, message_id))
            return BossActionResult("joined", state)

    @staticmethod
    def _event(conn: sqlite3.Connection, state: BossState, user_id: str, callback_query_id: str, phase: int, slot: int | None, now: datetime, accepted: bool) -> None:
        conn.execute(
            """INSERT INTO final_boss_events
            (chat_id, message_id, callback_query_id, user_id, phase, slot, pressed_at, accepted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (state.chat_id, state.message_id, callback_query_id, user_id, phase, slot, now.isoformat(), int(accepted)),
        )

    def expire(self, chat_id: str, message_id: str, now: datetime) -> BossActionResult:
        chat_id = self.db.resolve_chat_id(chat_id)
        with self.db._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            state = _read_state(conn, chat_id, message_id)
            if state is None:
                return BossActionResult("missing", None)
            if state.status != "active":
                return BossActionResult("finished", state)
            if now < datetime.fromisoformat(state.expires_at):
                return BossActionResult("not_due", state)
            reason = "abandoned" if state.phase == 1 and not state.phase1_users else "timeout"
            return self._finish(conn, state, now, reason)

    @staticmethod
    def _finish(conn: sqlite3.Connection, state: BossState, now: datetime, reason: str, offender: str | None = None, next_scheduled_for: datetime | None = None) -> BossActionResult:
        awards: dict[str, int] = {}
        won = reason == "won"
        if won:
            awards = {user: 100 for user in state.participant_user_ids}
            for user in state.phase1_users:
                awards[user] += 200
            for user, count in state.phase2_counts:
                awards[user] += count
            for _, user in state.phase3_slots:
                awards[user] += 100
            awards[state.final_user_id] += 500
        elif state.phase == 1:
            scores = conn.execute("SELECT user_id FROM hisopo_scores WHERE chat_id = ?", (state.chat_id,)).fetchall()
            awards = {str(row["user_id"]): -10 if reason == "abandoned" else -2 for row in scores if row["user_id"] not in state.phase1_users}
        elif state.phase in (3, 4):
            awards = {user: state.phase - 2 for user in state.participant_user_ids if user != offender}
        for user, points in awards.items():
            conn.execute(
                """INSERT INTO hisopo_scores (chat_id, user_id, points) VALUES (?, ?, ?)
                ON CONFLICT(chat_id, user_id) DO UPDATE SET points = hisopo_scores.points + excluded.points,
                updated_at = CURRENT_TIMESTAMP""", (state.chat_id, user, points)
            )
            if won:
                _increment_hisopo_collection(conn, state.chat_id, user, "final_boss", now.isoformat())
        if won and state.reveal_user_id is not None:
            _increment_hisopo_collection(conn, state.chat_id, state.reveal_user_id, "mystery", now.isoformat())
        conn.execute(
            """UPDATE final_boss_states SET status = ?, reason = ?, offender_user_id = ?, awards_json = ?
            WHERE chat_id = ? AND message_id = ?""",
            ("won" if won else "lost", reason, offender, json.dumps(sorted(awards.items())), state.chat_id, state.message_id),
        )
        conn.execute(
            """UPDATE hisopo_spawns SET status = ?, captured_at = ?, winner_user_id = ?,
            appearance_type = 'final_boss', message_cleanup_status = 'preserved'
            WHERE chat_id = ? AND message_id = ?""",
            ("captured" if won else "rotten", now.isoformat() if won else None, state.final_user_id, state.chat_id, state.message_id),
        )
        schedule = None
        if won and next_scheduled_for is not None:
            schedule = _insert_hisopo_schedule_below_daily_cap(conn, state.chat_id, next_scheduled_for, state.message_id)
        return BossActionResult("won" if won else "lost", _read_state(conn, state.chat_id, state.message_id), schedule)

    def get_pending_results(self) -> tuple[BossState, ...]:
        with self.db._connect() as conn:
            rows = conn.execute(
                "SELECT chat_id, message_id FROM final_boss_states WHERE status != 'active' AND announcement_complete = 0 ORDER BY chat_id, message_id"
            ).fetchall()
            return tuple(_read_state(conn, row["chat_id"], row["message_id"]) for row in rows)

    def mark_announced(self, chat_id: str, message_id: str, announcement_message_id: str) -> None:
        chat_id = self.db.resolve_chat_id(chat_id)
        if not announcement_message_id:
            raise ValueError("A confirmed announcement message ID is required.")
        with self.db._connect() as conn:
            conn.execute(
                """UPDATE final_boss_states SET announcement_message_id = ?
                WHERE chat_id = ? AND message_id = ? AND status != 'active' AND announcement_message_id IS NULL""",
                (announcement_message_id, chat_id, message_id),
            )

    def complete_announcement(self, chat_id: str, message_id: str) -> None:
        chat_id = self.db.resolve_chat_id(chat_id)
        with self.db._connect() as conn:
            conn.execute(
                """UPDATE final_boss_states SET announcement_complete = 1
                WHERE chat_id = ? AND message_id = ? AND status != 'active'
                AND announcement_message_id IS NOT NULL""", (chat_id, message_id)
            )
