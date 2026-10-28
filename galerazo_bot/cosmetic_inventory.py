"""Inventory provenance: transfers keep payment/refund and Club reward ownership."""
from __future__ import annotations

import sqlite3


MAX_QUANTITY = 2**63 - 1


def credit(conn: sqlite3.Connection, owner: str, item: str, source: str, quantity: int) -> None:
    conn.execute(
        "INSERT INTO cosmetic_lots (owner_id, item_key, source, quantity) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(owner_id, item_key, source) DO UPDATE SET quantity = quantity + excluded.quantity",
        (owner, item, source, quantity),
    )


def initialize(conn: sqlite3.Connection) -> None:
    if not conn.in_transaction:
        conn.execute('BEGIN IMMEDIATE')
    exists = conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'cosmetic_lots'").fetchone()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS cosmetic_lots (owner_id TEXT NOT NULL, item_key TEXT NOT NULL, "
        "source TEXT NOT NULL, quantity INTEGER NOT NULL CHECK (quantity > 0 AND typeof(quantity) = 'integer'), "
        "PRIMARY KEY (owner_id, item_key, source))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS cosmetic_transfers (sender_id TEXT NOT NULL, request_id TEXT NOT NULL, "
        "recipient_id TEXT NOT NULL, item_key TEXT NOT NULL, transferred_at TEXT NOT NULL, "
        "PRIMARY KEY (sender_id, request_id))"
    )
    if exists:
        return
    # One-time migration. Never enumerate units: legacy inventories may contain int64 maxima.
    for row in conn.execute("SELECT * FROM paid_hisopo_ownership").fetchall():
        owner, item, remaining = row['user_id'], row['hisopo_key'], row['quantity']
        payments = conn.execute(
            "SELECT telegram_payment_charge_id FROM star_payments WHERE status = 'paid' "
            "AND COALESCE(recipient_user_id, user_id) = ? AND reward_hisopo_key = ? ORDER BY rowid",
            (owner, item),
        ).fetchall()
        for payment in payments[:remaining]:
            credit(conn, owner, item, 'payment:' + payment[0], 1)
            remaining -= 1
        if item == 'stellar' and remaining:
            earned = conn.execute(
                "SELECT COALESCE(SUM(quantity_delta), 0) FROM club_reward_ledger WHERE user_id = ?", (owner,)
            ).fetchone()[0]
            quantity = min(remaining, max(0, earned))
            if quantity:
                credit(conn, owner, item, 'club:' + owner, quantity)
                remaining -= quantity
        if remaining:
            credit(conn, owner, item, 'legacy:' + owner, remaining)


def debit(conn: sqlite3.Connection, owner: str, item: str, quantity: int, timestamp: str) -> None:
    conn.execute(
        "DELETE FROM paid_hisopo_ownership WHERE user_id = ? AND hisopo_key = ? AND quantity <= ?",
        (owner, item, quantity),
    )
    conn.execute(
        "UPDATE paid_hisopo_ownership SET quantity = quantity - ?, last_acquired_at = ? "
        "WHERE user_id = ? AND hisopo_key = ?", (quantity, timestamp, owner, item),
    )


def remove_lot(conn: sqlite3.Connection, owner: str, item: str, source: str, quantity: int) -> None:
    conn.execute("DELETE FROM cosmetic_lots WHERE owner_id = ? AND item_key = ? AND source = ? AND quantity <= ?",
                 (owner, item, source, quantity))
    conn.execute("UPDATE cosmetic_lots SET quantity = quantity - ? WHERE owner_id = ? AND item_key = ? AND source = ?",
                 (quantity, owner, item, source))


def revoke(conn: sqlite3.Connection, item: str, source: str, quantity: int, timestamp: str) -> None:
    for row in conn.execute(
        "SELECT owner_id, quantity FROM cosmetic_lots WHERE item_key = ? AND source = ? ORDER BY owner_id",
        (item, source),
    ).fetchall():
        taken = min(quantity, row['quantity'])
        remove_lot(conn, row['owner_id'], item, source, taken)
        debit(conn, row['owner_id'], item, taken, timestamp)
        quantity -= taken
        if not quantity:
            break


def transfer(conn: sqlite3.Connection, sender: str, recipient: str, item: str, request_id: str, timestamp: str) -> None:
    previous = conn.execute(
        "SELECT recipient_id, item_key FROM cosmetic_transfers WHERE sender_id = ? AND request_id = ?",
        (sender, request_id),
    ).fetchone()
    if previous:
        if (previous['recipient_id'], previous['item_key']) != (recipient, item):
            raise ValueError('gift_conflict')
        return
    if sender == recipient:
        raise ValueError('gift_self')
    lot = conn.execute(
        "SELECT source FROM cosmetic_lots WHERE owner_id = ? AND item_key = ? ORDER BY source LIMIT 1",
        (sender, item),
    ).fetchone()
    if not lot:
        raise ValueError('gift_unavailable')
    inventory = conn.execute("SELECT quantity FROM paid_hisopo_ownership WHERE user_id = ? AND hisopo_key = ?",
                             (sender, item)).fetchone()
    if not inventory:
        raise ValueError('gift_unavailable')
    owned = conn.execute("SELECT quantity FROM paid_hisopo_ownership WHERE user_id = ? AND hisopo_key = ?",
                         (recipient, item)).fetchone()
    if owned and owned['quantity'] >= MAX_QUANTITY:
        raise ValueError('gift_full')
    conn.execute("INSERT INTO users (user_id) VALUES (?) ON CONFLICT(user_id) DO NOTHING", (recipient,))
    remove_lot(conn, sender, item, lot['source'], 1)
    debit(conn, sender, item, 1, timestamp)
    credit(conn, recipient, item, lot['source'], 1)
    conn.execute(
        "INSERT INTO paid_hisopo_ownership (user_id, hisopo_key, quantity, first_acquired_at, last_acquired_at) "
        "VALUES (?, ?, 1, ?, ?) ON CONFLICT(user_id, hisopo_key) DO UPDATE SET "
        "quantity = quantity + 1, last_acquired_at = excluded.last_acquired_at", (recipient, item, timestamp, timestamp),
    )
    conn.execute("INSERT INTO cosmetic_transfers VALUES (?, ?, ?, ?, ?)", (sender, request_id, recipient, item, timestamp))
