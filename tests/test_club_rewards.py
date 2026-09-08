from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from galerazo_bot.club_rewards import earned_rewards, reconcile_rewards
from galerazo_bot.database import Database
from galerazo_bot.telegram_bot import _club_rewards_job, _schedule_club_rewards


START = datetime(2030, 1, 1, tzinfo=timezone.utc)


def day(value: float) -> datetime:
    return START + timedelta(days=value)


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "club.sqlite3")


def pay(db, index, *, start=None, user="1", reward=None, expiration=True):
    start = index * 30 if start is None else start
    return db.record_star_payment(
        telegram_payment_charge_id=f"club-{user}-{index}", provider_payment_charge_id=None,
        user_id=user, kind="subscription", item_key="club", amount_stars=100, currency="XTR",
        invoice_payload="test", source_chat_id=None, reward_hisopo_key=reward,
        paid_at=day(start).isoformat(), is_recurring=True, is_first_recurring=index == 0,
        subscription_expiration_date=day(start + 30).isoformat() if expiration else None,
    )


def quantity(db, user="1"):
    return sum(row.quantity for row in db.get_paid_hisopo_ownership(user) if row.hisopo_key == "stellar")


def ledger(db):
    with db._connect() as conn:
        return [tuple(row) for row in conn.execute(
            "SELECT quantity_delta, earned_total FROM club_reward_ledger ORDER BY reward_id"
        )]


def test_first_reward_requires_elapsed_time_not_third_payment(db):
    for index in range(3):
        assert pay(db, index)
        assert db.reconcile_club_rewards(now=day(index * 30)) == 0
    assert db.reconcile_club_rewards(now=day(90) - timedelta(seconds=1)) == 0
    assert quantity(db) == 0
    assert db.reconcile_club_rewards(now=day(90)) == 1
    assert quantity(db) == 1
    assert ledger(db) == [(1, 1)]
    # No fourth payment is needed; the third paid period has fully elapsed.
    assert db.reconcile_club_rewards(now=day(180)) == 0
    assert quantity(db) == 1


def test_second_reward_restart_catchup_and_duplicate_payment(db):
    for index in range(6):
        pay(db, index)
    assert not pay(db, 2)
    assert db.reconcile_club_rewards(now=day(179)) == 1
    restarted = Database(db.path)
    assert restarted.reconcile_club_rewards(now=day(180)) == 1
    assert restarted.reconcile_club_rewards(now=day(360)) == 0
    assert quantity(restarted) == 2
    assert ledger(restarted) == [(1, 1), (1, 2)]


def test_downtime_can_catch_up_multiple_mature_rewards(db):
    for index in range(9):
        pay(db, index)
    assert db.reconcile_club_rewards(now=day(270)) == 3
    assert ledger(db) == [(3, 3)]


def test_gap_discards_incomplete_streak_and_preserves_completed_streak(db):
    for index in range(5):
        pay(db, index)
    # 150 days earns one; its unused 60 days cannot combine with the next streak.
    for index in range(5, 8):
        pay(db, index, start=200 + (index - 5) * 30)
    assert db.reconcile_club_rewards(now=day(260)) == 1
    assert db.reconcile_club_rewards(now=day(289)) == 0
    assert db.reconcile_club_rewards(now=day(290)) == 1
    assert quantity(db) == 2


def test_overlapping_subscriptions_and_out_of_order_updates_do_not_accelerate(db):
    for index, start in enumerate([60, 0, 30, 0, 0, 0]):
        pay(db, index, start=start)
    assert db.reconcile_club_rewards(now=day(60)) == 0
    assert db.reconcile_club_rewards(now=day(90)) == 1
    assert quantity(db) == 1


def test_single_second_gap_restarts_streak():
    expirations = [day(30).isoformat(), day(60).isoformat(),
                   (day(90) + timedelta(seconds=1)).isoformat()]
    assert earned_rewards(expirations, day(120)) == 0


def test_bad_missing_naive_and_future_dates_never_create_credit():
    values = [None, "invalid", "2030-02-01T00:00:00", day(30).isoformat()]
    assert earned_rewards(values, day(-1)) == 0
    assert earned_rewards(values, day(90)) == 0
    shifted = [(day(i) + timedelta(hours=3)).astimezone(timezone(timedelta(hours=3))).isoformat()
               for i in (30, 60, 90)]
    assert earned_rewards(shifted, day(90)) == 0
    assert earned_rewards(shifted, day(90) + timedelta(hours=3)) == 1


def test_old_stellar_payments_do_not_double_reward_but_support_periods_count(db):
    for index in range(3):
        pay(db, index, reward="stellar")
    assert quantity(db) == 3
    assert db.reconcile_club_rewards(now=day(90)) == 0
    for index in range(3, 6):
        pay(db, index)
    assert db.reconcile_club_rewards(now=day(180)) == 1
    assert quantity(db) == 4


def test_missing_expiration_does_not_count_as_one_completed_month(db):
    for index in range(3):
        pay(db, index, expiration=False)
    assert db.reconcile_club_rewards(now=day(365)) == 0


def test_refund_revokes_only_quarterly_rewards_and_preserves_gifts(db):
    db.grant_paid_hisopo(recipient_user_id="1", hisopo_key="stellar", gifted_by_user_id="2")
    for index in range(3):
        pay(db, index)
    db.reconcile_club_rewards(now=day(90))
    assert quantity(db) == 2
    assert db.refund_star_payment("club-1-1", refunded_at=day(91).isoformat())
    assert quantity(db) == 1
    assert ledger(db) == [(1, 1), (-1, 0)]
    assert not db.refund_star_payment("club-1-1", refunded_at=day(92).isoformat())
    assert db.reconcile_club_rewards(now=day(100)) == 0


def test_refund_removes_empty_ownership_and_a_new_streak_can_earn_again(db):
    for index in range(3):
        pay(db, index)
    db.reconcile_club_rewards(now=day(90))
    db.refund_star_payment("club-1-0", refunded_at=day(91).isoformat())
    assert quantity(db) == 0
    # The paid days 30..120 still form a valid 90-day streak after renewal.
    pay(db, 3)
    assert db.reconcile_club_rewards(now=day(120)) == 1
    assert quantity(db) == 1
    assert ledger(db) == [(1, 1), (-1, 0), (1, 1)]


def test_refund_before_maturity_and_clock_rollback(db):
    for index in range(6):
        pay(db, index)
    db.refund_star_payment("club-1-0", refunded_at=day(5).isoformat())
    assert db.reconcile_club_rewards(now=day(90)) == 0
    assert db.reconcile_club_rewards(now=day(120)) == 1
    assert db.reconcile_club_rewards(now=day(100)) == 0
    assert quantity(db) == 1


def test_normal_reconciliation_does_not_revoke_without_a_refund(db):
    for index in range(3):
        pay(db, index)
    db.reconcile_club_rewards(now=day(90))
    # Simulate an inconsistent historical row; only an explicit refund may revoke.
    with db._connect() as conn:
        conn.execute("UPDATE star_payments SET subscription_expiration_date = NULL")
    assert db.reconcile_club_rewards(now=day(100)) == 0
    assert quantity(db) == 1


def test_users_are_isolated_and_concurrent_checks_are_atomic(db):
    for user in ("1", "2"):
        for index in range(3):
            pay(db, index, user=user)
    with ThreadPoolExecutor(max_workers=2) as pool:
        deltas = list(pool.map(lambda _: db.reconcile_club_rewards(user_id="1", now=day(90)), range(2)))
    assert sorted(deltas) == [0, 1]
    assert quantity(db) == 1
    assert quantity(db, "2") == 0
    assert db.reconcile_club_rewards(now=day(90)) == 1
    assert quantity(db, "2") == 1


def test_transaction_failure_rolls_back_inventory_with_ledger(db):
    for index in range(3):
        pay(db, index)
    with db._connect() as conn:
        conn.execute("CREATE TRIGGER fail_reward BEFORE INSERT ON club_reward_ledger "
                     "BEGIN SELECT RAISE(ABORT, 'simulated failure'); END")
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError, match="simulated failure"):
        db.reconcile_club_rewards(now=day(90))
    assert quantity(db) == 0
    assert ledger(db) == []


@pytest.mark.asyncio
async def test_startup_and_periodic_job_work_without_miniapp():
    db = MagicMock()
    app = SimpleNamespace(bot_data={"db": db}, job_queue=MagicMock())
    _schedule_club_rewards(app)
    db.reconcile_club_rewards.assert_called_once_with()
    app.job_queue.run_repeating.assert_called_once_with(
        _club_rewards_job, interval=60, first=60, name="club-rewards")
    await _club_rewards_job(SimpleNamespace(application=app))
    assert db.reconcile_club_rewards.call_count == 2
