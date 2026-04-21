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
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (added_by_user_id) REFERENCES users (user_id)
                )
                """
            )
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
                SELECT chat_id, chat_type, title, added_by_user_id, created_at
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
                        updated_at = CURRENT_TIMESTAMP
                    WHERE chat_id = ?
                    """,
                    (old_chat["title"], old_chat["added_by_user_id"], new_chat_id),
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
