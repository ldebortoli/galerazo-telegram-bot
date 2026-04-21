from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class User:
    user_id: str
    display_name: str | None
    username: str | None


@dataclass(frozen=True)
class BlockedUser:
    user_id: str
    username: str | None
    display_name: str | None
    blocked_by_user_id: str
    blocked_at: str


@dataclass(frozen=True)
class ChatStatsRow:
    chat_type: str
    total: int
    active: int
    inactive: int


@dataclass(frozen=True)
class GalerazaScore:
    user_id: str
    username: str | None
    display_name: str | None
    points: int


@dataclass(frozen=True)
class GalerazaMessageState:
    chat_id: str
    message_id: str
    requester_user_id: str
    unlocked: bool
    current_page: int


@dataclass(frozen=True)
class PaginatedMessageState:
    chat_id: str
    message_id: str
    list_type: str
    requester_user_id: str
    content_json: str
    unlocked: bool
    current_page: int
    created_at: str


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    display_name TEXT,
                    username TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            _ensure_column(conn, "users", "username", "TEXT")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users (username)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chats (
                    chat_id TEXT PRIMARY KEY,
                    chat_type TEXT NOT NULL,
                    title TEXT,
                    added_by_user_id TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    status_reason TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (added_by_user_id) REFERENCES users (user_id)
                )
                """
            )
            _ensure_column(conn, "chats", "status", "TEXT NOT NULL DEFAULT 'active'")
            _ensure_column(conn, "chats", "status_reason", "TEXT")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_migrations (
                    old_chat_id TEXT PRIMARY KEY,
                    new_chat_id TEXT NOT NULL,
                    migrated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS incoming_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT,
                    sender_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (chat_id) REFERENCES chats (chat_id),
                    FOREIGN KEY (sender_id) REFERENCES users (user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS blocked_users (
                    user_id TEXT PRIMARY KEY,
                    blocked_by_user_id TEXT NOT NULL,
                    blocked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (blocked_by_user_id) REFERENCES users (user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS galeraza_daily_winners (
                    chat_id TEXT NOT NULL,
                    game_date TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    message_id TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (chat_id, game_date),
                    FOREIGN KEY (chat_id) REFERENCES chats (chat_id),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS galeraza_scores (
                    chat_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    points INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (chat_id, user_id),
                    FOREIGN KEY (chat_id) REFERENCES chats (chat_id),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS paginated_message_states (
                    chat_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    list_type TEXT NOT NULL,
                    requester_user_id TEXT NOT NULL,
                    content_json TEXT NOT NULL,
                    unlocked INTEGER NOT NULL DEFAULT 0,
                    current_page INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (chat_id, message_id),
                    FOREIGN KEY (chat_id) REFERENCES chats (chat_id),
                    FOREIGN KEY (requester_user_id) REFERENCES users (user_id)
                )
                """
            )
            _ensure_column(conn, "paginated_message_states", "content_json", "TEXT NOT NULL DEFAULT '{}'")
            _ensure_column(
                conn,
                "paginated_message_states",
                "current_page",
                "INTEGER NOT NULL DEFAULT 1",
            )
            if _table_exists(conn, "galeraza_message_states"):
                conn.execute(
                    """
                    INSERT OR IGNORE INTO paginated_message_states (
                        chat_id,
                        message_id,
                        list_type,
                        requester_user_id,
                        content_json,
                        unlocked,
                        current_page,
                        created_at,
                        updated_at
                    )
                    SELECT
                        chat_id,
                        message_id,
                        'galeraza',
                        requester_user_id,
                        '{}',
                        unlocked,
                        current_page,
                        created_at,
                        updated_at
                    FROM galeraza_message_states
                    """
                )

    def get_or_create_user(
        self,
        user_id: str,
        display_name: str | None = None,
        username: str | None = None,
    ) -> User:
        normalized_username = _normalize_username(username)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (user_id, display_name, username)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    display_name = COALESCE(excluded.display_name, users.display_name),
                    username = COALESCE(excluded.username, users.username),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, display_name, normalized_username),
            )
            row = conn.execute(
                "SELECT user_id, display_name, username FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()

        return User(
            user_id=row["user_id"],
            display_name=row["display_name"],
            username=row["username"],
        )

    def get_user(self, user_id: str) -> User | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT user_id, display_name, username FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()

        if row is None:
            return None

        return User(
            user_id=row["user_id"],
            display_name=row["display_name"],
            username=row["username"],
        )

    def get_user_by_username(self, username: str) -> User | None:
        normalized_username = _normalize_username(username)
        if not normalized_username:
            return None

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT user_id, display_name, username
                FROM users
                WHERE lower(username) = lower(?)
                """,
                (normalized_username,),
            ).fetchone()

        if row is None:
            return None

        return User(
            user_id=row["user_id"],
            display_name=row["display_name"],
            username=row["username"],
        )

    def register_chat(
        self,
        chat_id: str,
        chat_type: str,
        title: str | None = None,
        added_by_user_id: str | None = None,
    ) -> None:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chats (chat_id, chat_type, title, added_by_user_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    chat_type = excluded.chat_type,
                    title = COALESCE(excluded.title, chats.title),
                    added_by_user_id = COALESCE(excluded.added_by_user_id, chats.added_by_user_id),
                    status = 'active',
                    status_reason = NULL,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (chat_id, chat_type, title, added_by_user_id),
            )

    def migrate_chat_id(self, old_chat_id: str, new_chat_id: str) -> None:
        if old_chat_id == new_chat_id:
            return

        with self._connect() as conn:
            old_chat = conn.execute(
                """
                SELECT chat_id, chat_type, title, added_by_user_id, status, status_reason, created_at
                FROM chats
                WHERE chat_id = ?
                """,
                (old_chat_id,),
            ).fetchone()
            new_chat = conn.execute(
                "SELECT chat_id FROM chats WHERE chat_id = ?",
                (new_chat_id,),
            ).fetchone()

            if old_chat and new_chat:
                conn.execute(
                    """
                    UPDATE chats
                    SET
                        title = COALESCE(title, ?),
                        added_by_user_id = COALESCE(added_by_user_id, ?),
                        status = ?,
                        status_reason = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE chat_id = ?
                    """,
                    (
                        old_chat["title"],
                        old_chat["added_by_user_id"],
                        old_chat["status"],
                        old_chat["status_reason"],
                        new_chat_id,
                    ),
                )
                conn.execute("DELETE FROM chats WHERE chat_id = ?", (old_chat_id,))
            elif old_chat:
                conn.execute(
                    """
                    UPDATE chats
                    SET
                        chat_id = ?,
                        chat_type = 'supergroup',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE chat_id = ?
                    """,
                    (new_chat_id, old_chat_id),
                )
            elif not new_chat:
                conn.execute(
                    """
                    INSERT INTO chats (chat_id, chat_type)
                    VALUES (?, 'supergroup')
                    """,
                    (new_chat_id,),
                )

            conn.execute(
                "UPDATE incoming_messages SET chat_id = ? WHERE chat_id = ?",
                (new_chat_id, old_chat_id),
            )
            conn.execute(
                "UPDATE galeraza_daily_winners SET chat_id = ? WHERE chat_id = ?",
                (new_chat_id, old_chat_id),
            )
            old_scores = conn.execute(
                """
                SELECT user_id, points
                FROM galeraza_scores
                WHERE chat_id = ?
                """,
                (old_chat_id,),
            ).fetchall()
            for score in old_scores:
                conn.execute(
                    """
                    INSERT INTO galeraza_scores (chat_id, user_id, points, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(chat_id, user_id) DO UPDATE SET
                        points = galeraza_scores.points + excluded.points,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (new_chat_id, score["user_id"], score["points"]),
                )
            conn.execute("DELETE FROM galeraza_scores WHERE chat_id = ?", (old_chat_id,))
            conn.execute(
                "UPDATE paginated_message_states SET chat_id = ? WHERE chat_id = ?",
                (new_chat_id, old_chat_id),
            )
            conn.execute(
                """
                INSERT INTO chat_migrations (old_chat_id, new_chat_id)
                VALUES (?, ?)
                ON CONFLICT(old_chat_id) DO UPDATE SET
                    new_chat_id = excluded.new_chat_id,
                    migrated_at = CURRENT_TIMESTAMP
                """,
                (old_chat_id, new_chat_id),
            )

    def resolve_chat_id(self, chat_id: str) -> str:
        with self._connect() as conn:
            current_chat_id = chat_id
            seen: set[str] = set()

            while current_chat_id not in seen:
                seen.add(current_chat_id)
                row = conn.execute(
                    "SELECT new_chat_id FROM chat_migrations WHERE old_chat_id = ?",
                    (current_chat_id,),
                ).fetchone()
                if row is None:
                    return current_chat_id
                current_chat_id = row["new_chat_id"]

        return current_chat_id

    def get_chat_added_by_user_id(self, chat_id: str) -> str | None:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT added_by_user_id FROM chats WHERE chat_id = ?",
                (chat_id,),
            ).fetchone()
        return row["added_by_user_id"] if row else None

    def mark_chat_inactive(self, chat_id: str, reason: str) -> None:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE chats
                SET
                    status = 'inactive',
                    status_reason = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE chat_id = ?
                """,
                (reason, chat_id),
            )

    def get_chat_stats(self) -> list[ChatStatsRow]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    chat_type,
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active,
                    SUM(CASE WHEN status != 'active' THEN 1 ELSE 0 END) AS inactive
                FROM chats
                GROUP BY chat_type
                """
            ).fetchall()

        return [
            ChatStatsRow(
                chat_type=row["chat_type"],
                total=row["total"],
                active=row["active"] or 0,
                inactive=row["inactive"] or 0,
            )
            for row in rows
        ]

    def save_incoming_message(
        self,
        sender_id: str,
        text: str,
        chat_id: str | None = None,
    ) -> None:
        self.get_or_create_user(sender_id)
        if chat_id is not None:
            chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO incoming_messages (chat_id, sender_id, text) VALUES (?, ?, ?)",
                (chat_id, sender_id, text),
            )

    def block_user(self, user_id: str, blocked_by_user_id: str) -> None:
        self.get_or_create_user(user_id)
        self.get_or_create_user(blocked_by_user_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO blocked_users (user_id, blocked_by_user_id)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    blocked_by_user_id = excluded.blocked_by_user_id,
                    blocked_at = CURRENT_TIMESTAMP
                """,
                (user_id, blocked_by_user_id),
            )

    def unblock_user(self, user_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM blocked_users WHERE user_id = ?",
                (user_id,),
            )
        return cursor.rowcount > 0

    def is_user_blocked(self, user_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM blocked_users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return row is not None

    def list_blocked_users(self) -> list[BlockedUser]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    blocked_users.user_id,
                    users.username,
                    users.display_name,
                    blocked_users.blocked_by_user_id,
                    blocked_users.blocked_at
                FROM blocked_users
                LEFT JOIN users ON users.user_id = blocked_users.user_id
                ORDER BY blocked_users.blocked_at DESC
                """
            ).fetchall()

        return [
            BlockedUser(
                user_id=row["user_id"],
                username=row["username"],
                display_name=row["display_name"],
                blocked_by_user_id=row["blocked_by_user_id"],
                blocked_at=row["blocked_at"],
            )
            for row in rows
        ]

    def create_backup(self, backups_dir: Path) -> Path:
        backups_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = backups_dir / f"galerazo-backup-{timestamp}.sqlite3"

        source = sqlite3.connect(self.path)
        try:
            destination = sqlite3.connect(backup_path)
            try:
                source.backup(destination)
            finally:
                destination.close()
        finally:
            source.close()

        return backup_path

    def try_award_daily_galeraza(
        self,
        chat_id: str,
        game_date: str,
        user_id: str,
        message_id: str,
    ) -> bool:
        chat_id = self.resolve_chat_id(chat_id)
        self.get_or_create_user(user_id)
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO galeraza_daily_winners (
                    chat_id,
                    game_date,
                    user_id,
                    message_id
                )
                VALUES (?, ?, ?, ?)
                """,
                (chat_id, game_date, user_id, message_id),
            )
            if cursor.rowcount == 0:
                return False

            conn.execute(
                """
                INSERT INTO galeraza_scores (chat_id, user_id, points)
                VALUES (?, ?, 1)
                ON CONFLICT(chat_id, user_id) DO UPDATE SET
                    points = points + 1,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (chat_id, user_id),
            )

        return True

    def get_galeraza_scores(self, chat_id: str) -> list[GalerazaScore]:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    galeraza_scores.user_id,
                    users.username,
                    users.display_name,
                    galeraza_scores.points
                FROM galeraza_scores
                LEFT JOIN users ON users.user_id = galeraza_scores.user_id
                WHERE galeraza_scores.chat_id = ?
                ORDER BY galeraza_scores.points DESC, lower(COALESCE(users.display_name, users.username, galeraza_scores.user_id)) ASC
                """,
                (chat_id,),
            ).fetchall()

        return [
            GalerazaScore(
                user_id=row["user_id"],
                username=row["username"],
                display_name=row["display_name"],
                points=row["points"],
            )
            for row in rows
        ]

    def save_paginated_message_state(
        self,
        chat_id: str,
        message_id: str,
        list_type: str,
        requester_user_id: str,
        content_json: str,
        unlocked: bool = False,
        current_page: int = 1,
    ) -> None:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO paginated_message_states (
                    chat_id,
                    message_id,
                    list_type,
                    requester_user_id,
                    content_json,
                    unlocked,
                    current_page
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id, message_id) DO UPDATE SET
                    list_type = excluded.list_type,
                    requester_user_id = excluded.requester_user_id,
                    content_json = excluded.content_json,
                    unlocked = excluded.unlocked,
                    current_page = excluded.current_page,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    chat_id,
                    message_id,
                    list_type,
                    requester_user_id,
                    content_json,
                    int(unlocked),
                    current_page,
                ),
            )

    def get_paginated_message_state(
        self,
        chat_id: str,
        message_id: str,
    ) -> PaginatedMessageState | None:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    chat_id,
                    message_id,
                    list_type,
                    requester_user_id,
                    content_json,
                    unlocked,
                    current_page,
                    created_at
                FROM paginated_message_states
                WHERE chat_id = ? AND message_id = ?
                """,
                (chat_id, message_id),
            ).fetchone()

        if row is None:
            return None

        return PaginatedMessageState(
            chat_id=row["chat_id"],
            message_id=row["message_id"],
            list_type=row["list_type"],
            requester_user_id=row["requester_user_id"],
            content_json=row["content_json"],
            unlocked=bool(row["unlocked"]),
            current_page=row["current_page"],
            created_at=row["created_at"],
        )

    def list_paginated_message_states_before(self, cutoff: str) -> list[PaginatedMessageState]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    chat_id,
                    message_id,
                    list_type,
                    requester_user_id,
                    content_json,
                    unlocked,
                    current_page,
                    created_at
                FROM paginated_message_states
                WHERE created_at < ?
                ORDER BY created_at ASC
                """,
                (cutoff,),
            ).fetchall()

        return [
            PaginatedMessageState(
                chat_id=row["chat_id"],
                message_id=row["message_id"],
                list_type=row["list_type"],
                requester_user_id=row["requester_user_id"],
                content_json=row["content_json"],
                unlocked=bool(row["unlocked"]),
                current_page=row["current_page"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def set_paginated_message_unlocked(
        self,
        chat_id: str,
        message_id: str,
        unlocked: bool,
    ) -> None:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE paginated_message_states
                SET unlocked = ?, updated_at = CURRENT_TIMESTAMP
                WHERE chat_id = ? AND message_id = ?
                """,
                (int(unlocked), chat_id, message_id),
            )

    def set_paginated_message_page(
        self,
        chat_id: str,
        message_id: str,
        current_page: int,
    ) -> None:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE paginated_message_states
                SET current_page = ?, updated_at = CURRENT_TIMESTAMP
                WHERE chat_id = ? AND message_id = ?
                """,
                (current_page, chat_id, message_id),
            )

    def delete_paginated_message_state(self, chat_id: str, message_id: str) -> None:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            conn.execute(
                """
                DELETE FROM paginated_message_states
                WHERE chat_id = ? AND message_id = ?
                """,
                (chat_id, message_id),
            )

    def save_galeraza_message_state(
        self,
        chat_id: str,
        message_id: str,
        requester_user_id: str,
        unlocked: bool = False,
        current_page: int = 1,
    ) -> None:
        self.save_paginated_message_state(
            chat_id,
            message_id,
            "galeraza",
            requester_user_id,
            "{}",
            unlocked,
            current_page,
        )

    def get_galeraza_message_state(
        self,
        chat_id: str,
        message_id: str,
    ) -> PaginatedMessageState | None:
        return self.get_paginated_message_state(chat_id, message_id)

    def set_galeraza_message_unlocked(self, chat_id: str, message_id: str, unlocked: bool) -> None:
        self.set_paginated_message_unlocked(chat_id, message_id, unlocked)

    def set_galeraza_message_page(self, chat_id: str, message_id: str, current_page: int) -> None:
        self.set_paginated_message_page(chat_id, message_id, current_page)

    def delete_galeraza_message_state(self, chat_id: str, message_id: str) -> None:
        self.delete_paginated_message_state(chat_id, message_id)


def _normalize_username(username: str | None) -> str | None:
    if not username:
        return None
    return username.removeprefix("@").strip() or None


def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    columns = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None
