from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone


CLUB_PERIOD = timedelta(days=30)
CLUB_REWARD_INTERVAL = timedelta(days=90)
CLUB_REWARD_KEY = "stellar"


def earned_rewards(expirations: list[str | None], now: datetime) -> int:
    """Count completed 90-day blocks of continuous, paid Telegram coverage.

    Telegram defines each paid period by its expiration and fixed 30-day length.
    Merge overlaps so concurrent subscriptions never speed up the reward clock.
    A gap starts a new streak; already completed streaks remain earned.
    """
    intervals = []
    for value in expirations:
        try:
            end = datetime.fromisoformat(value or "")
        except ValueError:
            continue
        if end.tzinfo is None:
            continue
        start = end - CLUB_PERIOD
        end = min(end, now)
        if start < end:
            intervals.append((start, end))
    total = 0
    streak_start = streak_end = None
    for start, end in sorted(intervals):
        if streak_end is None or start > streak_end:
            if streak_end is not None:
                total += (streak_end - streak_start) // CLUB_REWARD_INTERVAL
            streak_start, streak_end = start, end
        else:
            streak_end = max(streak_end, end)
    if streak_end is not None:
        total += (streak_end - streak_start) // CLUB_REWARD_INTERVAL
    return total


def reconcile_rewards(
    conn: sqlite3.Connection,
    now: datetime,
    *,
    user_id: str | None = None,
    allow_revoke: bool = False,
) -> int:
    """Caller owns the write transaction; ledger and inventory commit together."""
    users = [user_id] if user_id is not None else [
        row["user_id"] for row in conn.execute("SELECT user_id FROM club_memberships")
    ]
    total_delta = 0
    for member_id in users:
        previous = conn.execute(
            "SELECT COALESCE(SUM(quantity_delta), 0) AS quantity, MAX(evaluated_at) AS evaluated_at "
            "FROM club_reward_ledger WHERE user_id = ?", (member_id,),
        ).fetchone()
        # A clock correction or an old refund update must not undo elapsed time.
        evaluated_at = max(now, datetime.fromisoformat(previous["evaluated_at"])) if previous["evaluated_at"] else now
        periods = conn.execute(
            "SELECT subscription_expiration_date FROM star_payments "
            "WHERE user_id = ? AND kind = 'subscription' AND item_key = 'club' "
            "AND status = 'paid' AND reward_hisopo_key = ''", (member_id,),
        ).fetchall()
        earned = earned_rewards([row["subscription_expiration_date"] for row in periods], evaluated_at)
        delta = earned - previous["quantity"]
        if delta == 0 or (delta < 0 and not allow_revoke):
            continue
        timestamp = now.astimezone(timezone.utc).isoformat()
        if delta > 0:
            conn.execute(
                "INSERT INTO paid_hisopo_ownership "
                "(user_id, hisopo_key, quantity, first_acquired_at, last_acquired_at) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT(user_id, hisopo_key) DO UPDATE SET "
                "quantity = paid_hisopo_ownership.quantity + excluded.quantity, "
                "last_acquired_at = excluded.last_acquired_at",
                (member_id, CLUB_REWARD_KEY, delta, timestamp, timestamp),
            )
        else:
            conn.execute(
                "DELETE FROM paid_hisopo_ownership WHERE user_id = ? AND hisopo_key = ? AND quantity <= ?",
                (member_id, CLUB_REWARD_KEY, -delta),
            )
            conn.execute(
                "UPDATE paid_hisopo_ownership SET quantity = quantity + ?, last_acquired_at = ? "
                "WHERE user_id = ? AND hisopo_key = ?",
                (delta, timestamp, member_id, CLUB_REWARD_KEY),
            )
        conn.execute(
            "INSERT INTO club_reward_ledger "
            "(user_id, quantity_delta, earned_total, evaluated_at, processed_at) VALUES (?, ?, ?, ?, ?)",
            (member_id, delta, earned, evaluated_at.astimezone(timezone.utc).isoformat(), timestamp),
        )
        total_delta += delta
    return total_delta
