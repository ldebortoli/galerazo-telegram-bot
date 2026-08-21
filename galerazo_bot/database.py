from __future__ import annotations

import secrets
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


MAX_HISOPO_SCHEDULES_PER_CHAT_DAY = 10
_ARGENTINA_TIMEZONE = ZoneInfo("America/Argentina/Buenos_Aires")


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
class ChatRestrictedUser:
    chat_id: str
    user_id: str
    username: str | None
    display_name: str | None
    restricted_by_user_id: str
    restricted_at: str


@dataclass(frozen=True)
class ChatStatsRow:
    chat_type: str
    total: int
    active: int
    inactive: int


@dataclass(frozen=True)
class ActiveChat:
    chat_id: str
    chat_type: str
    title: str | None


@dataclass(frozen=True)
class ChatSettings:
    chat_id: str
    language: str
    announcements_enabled: bool


@dataclass(frozen=True)
class GalerazaScore:
    user_id: str
    username: str | None
    display_name: str | None
    points: int


@dataclass(frozen=True)
class HisopoScore:
    user_id: str
    username: str | None
    display_name: str | None
    points: int


@dataclass(frozen=True)
class HisopoCollectionEntry:
    hisopo_type: str
    capture_count: int
    first_captured_at: str
    last_captured_at: str


@dataclass(frozen=True)
class HisopoSpawn:
    chat_id: str
    message_id: str
    hisopo_type: str
    appearance_type: str
    points: int
    source: str
    spawned_at: str
    expires_at: str
    status: str
    winner_user_id: str | None
    captured_at: str | None
    required_helpers: int = 1


@dataclass(frozen=True)
class HisopoMessageCleanup:
    chat_id: str
    message_id: str
    spawned_at: str
    attempts: int
    last_attempt_at: str | None


@dataclass(frozen=True)
class HisopoSchedule:
    schedule_id: int
    chat_id: str
    scheduled_for: str
    status: str
    source_message_id: str


@dataclass(frozen=True)
class HisopoCaptureResult:
    status: str
    spawn: HisopoSpawn | None
    schedule: HisopoSchedule | None = None
    additional_schedules: tuple[HisopoSchedule, ...] = ()

    @property
    def schedules(self) -> tuple[HisopoSchedule, ...]:
        if self.schedule is None:
            return self.additional_schedules
        return (self.schedule, *self.additional_schedules)


@dataclass(frozen=True)
class HisopoGiantContributionResult:
    status: str
    spawn: HisopoSpawn | None
    participant_user_ids: tuple[str, ...] = ()
    contribution_count: int = 0
    required_helpers: int = 0
    schedule: HisopoSchedule | None = None
    revealed: bool = False


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


@dataclass(frozen=True)
class RestartConfirmation:
    chat_id: str
    message_id: str
    requester_user_id: str
    created_at: str


@dataclass(frozen=True)
class Trigger:
    chat_id: str
    trigger_name: str
    display_name: str
    text: str | None
    media_type: str | None
    file_id: str | None
    caption: str | None
    created_by_user_id: str
    created_at: str
    payload_json: str | None = None


@dataclass(frozen=True)
class Expense:
    expense_id: int
    chat_id: str
    user_id: str
    username: str | None
    display_name: str | None
    amount_cents: int
    currency: str
    payment_method: str
    source: str
    description: str
    sheet_status: str
    sheet_error: str | None
    created_at: str
    synced_at: str | None


@dataclass(frozen=True)
class RussianRouletteShot:
    hit: bool
    remaining_shots: int


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    migration_id TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
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
                CREATE TABLE IF NOT EXISTS chat_settings (
                    chat_id TEXT PRIMARY KEY,
                    language TEXT NOT NULL DEFAULT 'es',
                    announcements_enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (chat_id) REFERENCES chats (chat_id)
                )
                """
            )
            _ensure_column(conn, "chat_settings", "announcements_enabled", "INTEGER NOT NULL DEFAULT 1")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_command_settings (
                    chat_id TEXT NOT NULL,
                    command_group TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (chat_id, command_group),
                    FOREIGN KEY (chat_id) REFERENCES chats (chat_id)
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
                CREATE TABLE IF NOT EXISTS chat_restricted_users (
                    chat_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    restricted_by_user_id TEXT NOT NULL,
                    restricted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (chat_id, user_id),
                    FOREIGN KEY (chat_id) REFERENCES chats (chat_id),
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (restricted_by_user_id) REFERENCES users (user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_user_reports (
                    user_id TEXT NOT NULL,
                    report_date TEXT NOT NULL,
                    chat_id TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, report_date),
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (chat_id) REFERENCES chats (chat_id)
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
                    message_date TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (chat_id, game_date),
                    FOREIGN KEY (chat_id) REFERENCES chats (chat_id),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
                """
            )
            _ensure_column(conn, "galeraza_daily_winners", "message_date", "TEXT")
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
                CREATE TABLE IF NOT EXISTS hisopo_chat_settings (
                    chat_id TEXT PRIMARY KEY,
                    intensity_percent INTEGER NOT NULL DEFAULT 10,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (chat_id) REFERENCES chats (chat_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS hisopo_spawns (
                    chat_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    hisopo_type TEXT NOT NULL,
                    appearance_type TEXT NOT NULL,
                    points INTEGER NOT NULL,
                    required_helpers INTEGER NOT NULL DEFAULT 1,
                    source TEXT NOT NULL,
                    spawned_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    winner_user_id TEXT,
                    captured_at TEXT,
                    message_cleanup_status TEXT NOT NULL DEFAULT 'pending',
                    message_cleanup_attempts INTEGER NOT NULL DEFAULT 0,
                    message_cleanup_last_attempt_at TEXT,
                    message_deleted_at TEXT,
                    message_cleanup_error TEXT,
                    PRIMARY KEY (chat_id, message_id),
                    FOREIGN KEY (chat_id) REFERENCES chats (chat_id),
                    FOREIGN KEY (winner_user_id) REFERENCES users (user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS hisopo_scores (
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
                CREATE TABLE IF NOT EXISTS hisopo_collections (
                    chat_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    hisopo_type TEXT NOT NULL,
                    capture_count INTEGER NOT NULL DEFAULT 0,
                    first_captured_at TEXT NOT NULL,
                    last_captured_at TEXT NOT NULL,
                    PRIMARY KEY (chat_id, user_id, hisopo_type),
                    FOREIGN KEY (chat_id) REFERENCES chats (chat_id),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS hisopo_schedules (
                    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    scheduled_for TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    source_message_id TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    FOREIGN KEY (chat_id) REFERENCES chats (chat_id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_hisopo_schedules_pending
                ON hisopo_schedules (status, scheduled_for)
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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS restart_confirmations (
                    chat_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    requester_user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (chat_id, message_id),
                    FOREIGN KEY (chat_id) REFERENCES chats (chat_id),
                    FOREIGN KEY (requester_user_id) REFERENCES users (user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS triggers (
                    chat_id TEXT NOT NULL,
                    trigger_name TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    text TEXT,
                    media_type TEXT,
                    file_id TEXT,
                    caption TEXT,
                    payload_json TEXT,
                    created_by_user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (chat_id, trigger_name),
                    FOREIGN KEY (chat_id) REFERENCES chats (chat_id),
                    FOREIGN KEY (created_by_user_id) REFERENCES users (user_id)
                )
                """
            )
            _ensure_column(conn, "triggers", "payload_json", "TEXT")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS expenses (
                    expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    currency TEXT NOT NULL DEFAULT 'ARS',
                    payment_method TEXT NOT NULL,
                    source TEXT NOT NULL,
                    description TEXT NOT NULL,
                    sheet_status TEXT NOT NULL DEFAULT 'pending',
                    sheet_error TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    synced_at TEXT,
                    FOREIGN KEY (chat_id) REFERENCES chats (chat_id),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS russian_roulette_states (
                    chat_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    bullet_position INTEGER NOT NULL CHECK (bullet_position BETWEEN 0 AND 5),
                    shots_fired INTEGER NOT NULL DEFAULT 0 CHECK (shots_fired BETWEEN 0 AND 5),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (chat_id, user_id),
                    FOREIGN KEY (chat_id) REFERENCES chats (chat_id),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS release_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    announced_version TEXT NOT NULL,
                    announced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
            self._apply_schema_migrations(conn)

    @staticmethod
    def _apply_schema_migrations(conn: sqlite3.Connection) -> None:
        migration_id = "20260729_drop_legacy_galeraza_message_states"
        applied = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE migration_id = ?", (migration_id,)
        ).fetchone()
        if applied is None:
            conn.execute("DROP TABLE IF EXISTS galeraza_message_states")
            conn.execute("INSERT INTO schema_migrations (migration_id) VALUES (?)", (migration_id,))

        migration_id = "20260820_add_cooperative_hisopos"
        applied = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE migration_id = ?", (migration_id,)
        ).fetchone()
        if applied is None:
            _ensure_column(
                conn,
                "hisopo_spawns",
                "required_helpers",
                "INTEGER NOT NULL DEFAULT 1",
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS hisopo_giant_contributions (
                    chat_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    contributed_at TEXT NOT NULL,
                    PRIMARY KEY (chat_id, message_id, user_id),
                    FOREIGN KEY (chat_id, message_id)
                        REFERENCES hisopo_spawns (chat_id, message_id),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
                """
            )
            conn.execute(
                "INSERT INTO schema_migrations (migration_id) VALUES (?)",
                (migration_id,),
            )

        migration_id = "20260820_add_hisopo_appearance_type"
        applied = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE migration_id = ?", (migration_id,)
        ).fetchone()
        if applied is None:
            _ensure_column(conn, "hisopo_spawns", "appearance_type", "TEXT")
            conn.execute(
                "UPDATE hisopo_spawns SET appearance_type = hisopo_type "
                "WHERE appearance_type IS NULL"
            )
            conn.execute("INSERT INTO schema_migrations (migration_id) VALUES (?)", (migration_id,))

        migration_id = "20260820_add_hisopo_collections"
        applied = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE migration_id = ?", (migration_id,)
        ).fetchone()
        if applied is None:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS hisopo_collections (
                    chat_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    hisopo_type TEXT NOT NULL,
                    capture_count INTEGER NOT NULL DEFAULT 0,
                    first_captured_at TEXT NOT NULL,
                    last_captured_at TEXT NOT NULL,
                    PRIMARY KEY (chat_id, user_id, hisopo_type),
                    FOREIGN KEY (chat_id) REFERENCES chats (chat_id),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
                """
            )
            conn.execute(
                """
                INSERT INTO hisopo_collections (
                    chat_id, user_id, hisopo_type, capture_count,
                    first_captured_at, last_captured_at
                )
                SELECT
                    chat_id,
                    winner_user_id,
                    hisopo_type,
                    COUNT(*),
                    MIN(captured_at),
                    MAX(captured_at)
                FROM hisopo_spawns
                WHERE status = 'captured'
                  AND winner_user_id IS NOT NULL
                  AND captured_at IS NOT NULL
                  AND hisopo_type != 'giant'
                  AND NOT (
                      hisopo_type = 'fleeting'
                      AND appearance_type = 'mystery'
                      AND points = 0
                  )
                GROUP BY chat_id, winner_user_id, hisopo_type
                """
            )
            conn.execute(
                """
                INSERT INTO hisopo_collections (
                    chat_id, user_id, hisopo_type, capture_count,
                    first_captured_at, last_captured_at
                )
                SELECT
                    contribution.chat_id,
                    contribution.user_id,
                    'giant',
                    COUNT(*),
                    MIN(spawn.captured_at),
                    MAX(spawn.captured_at)
                FROM hisopo_giant_contributions AS contribution
                JOIN hisopo_spawns AS spawn
                  ON spawn.chat_id = contribution.chat_id
                 AND spawn.message_id = contribution.message_id
                WHERE spawn.status = 'captured'
                  AND spawn.hisopo_type = 'giant'
                  AND spawn.captured_at IS NOT NULL
                GROUP BY contribution.chat_id, contribution.user_id
                """
            )
            conn.execute(
                "INSERT INTO schema_migrations (migration_id) VALUES (?)",
                (migration_id,),
            )

        migration_id = "20260821_add_hisopo_message_cleanup"
        applied = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE migration_id = ?", (migration_id,)
        ).fetchone()
        if applied is None:
            _ensure_column(
                conn,
                "hisopo_spawns",
                "message_cleanup_status",
                "TEXT NOT NULL DEFAULT 'pending'",
            )
            _ensure_column(
                conn,
                "hisopo_spawns",
                "message_cleanup_attempts",
                "INTEGER NOT NULL DEFAULT 0",
            )
            _ensure_column(
                conn,
                "hisopo_spawns",
                "message_cleanup_last_attempt_at",
                "TEXT",
            )
            _ensure_column(conn, "hisopo_spawns", "message_deleted_at", "TEXT")
            _ensure_column(conn, "hisopo_spawns", "message_cleanup_error", "TEXT")
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_hisopo_spawns_message_cleanup
                ON hisopo_spawns (chat_id, message_cleanup_status, spawned_at)
                """
            )
            conn.execute(
                "INSERT INTO schema_migrations (migration_id) VALUES (?)",
                (migration_id,),
            )

    def get_announced_release_version(self) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT announced_version FROM release_state WHERE id = 1"
            ).fetchone()
        return str(row["announced_version"]) if row is not None else None

    def set_announced_release_version(self, version: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO release_state (id, announced_version, announced_at)
                VALUES (1, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    announced_version = excluded.announced_version,
                    announced_at = CURRENT_TIMESTAMP
                """,
                (version,),
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

    def migrate_chat_id(self, old_chat_id: str, new_chat_id: str) -> bool:
        if old_chat_id == new_chat_id:
            return False

        with self._connect() as conn:
            migration_claim = conn.execute(
                """
                INSERT INTO chat_migrations (old_chat_id, new_chat_id)
                VALUES (?, ?)
                ON CONFLICT(old_chat_id) DO NOTHING
                """,
                (old_chat_id, new_chat_id),
            )
            if migration_claim.rowcount == 0:
                return False

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
            from .chat_migration import migrate_command_data

            migrate_command_data(conn, old_chat_id, new_chat_id)

        return True

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

    def get_chat_settings(self, chat_id: str) -> ChatSettings:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_settings (chat_id)
                VALUES (?)
                ON CONFLICT(chat_id) DO NOTHING
                """,
                (chat_id,),
            )
            row = conn.execute(
                "SELECT chat_id, language, announcements_enabled FROM chat_settings WHERE chat_id = ?",
                (chat_id,),
            ).fetchone()

        return ChatSettings(
            chat_id=row["chat_id"],
            language=row["language"],
            announcements_enabled=bool(row["announcements_enabled"]),
        )

    def set_chat_language(self, chat_id: str, language: str) -> None:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_settings (chat_id, language)
                VALUES (?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    language = excluded.language,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (chat_id, language),
            )

    def set_chat_announcements_enabled(self, chat_id: str, enabled: bool) -> None:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_settings (chat_id, announcements_enabled)
                VALUES (?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    announcements_enabled = excluded.announcements_enabled,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (chat_id, int(enabled)),
            )

    def is_command_group_enabled(self, chat_id: str, command_group: str) -> bool:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT enabled
                FROM chat_command_settings
                WHERE chat_id = ? AND command_group = ?
                """,
                (chat_id, command_group),
            ).fetchone()
        if row is None:
            return command_group not in {"gastos", "ruletarusa"}
        return bool(row["enabled"])

    def set_command_group_enabled(self, chat_id: str, command_group: str, enabled: bool) -> None:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_command_settings (chat_id, command_group, enabled)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id, command_group) DO UPDATE SET
                    enabled = excluded.enabled,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (chat_id, command_group, int(enabled)),
            )

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

    def list_active_chats(self) -> list[ActiveChat]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT chat_id, chat_type, title
                FROM chats
                WHERE status = 'active'
                ORDER BY chat_id
                """
            ).fetchall()
        return [ActiveChat(row["chat_id"], row["chat_type"], row["title"]) for row in rows]

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

    def restrict_user_in_chat(self, chat_id: str, user_id: str, restricted_by_user_id: str) -> None:
        chat_id = self.resolve_chat_id(chat_id)
        self.get_or_create_user(user_id)
        self.get_or_create_user(restricted_by_user_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_restricted_users (chat_id, user_id, restricted_by_user_id)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id, user_id) DO UPDATE SET
                    restricted_by_user_id = excluded.restricted_by_user_id,
                    restricted_at = CURRENT_TIMESTAMP
                """,
                (chat_id, user_id, restricted_by_user_id),
            )

    def unrestrict_user_in_chat(self, chat_id: str, user_id: str) -> bool:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM chat_restricted_users WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id),
            )
        return cursor.rowcount > 0

    def is_user_restricted_in_chat(self, chat_id: str, user_id: str) -> bool:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM chat_restricted_users
                WHERE chat_id = ? AND user_id = ?
                """,
                (chat_id, user_id),
            ).fetchone()
        return row is not None

    def list_restricted_users_in_chat(self, chat_id: str) -> list[ChatRestrictedUser]:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    chat_restricted_users.chat_id,
                    chat_restricted_users.user_id,
                    users.username,
                    users.display_name,
                    chat_restricted_users.restricted_by_user_id,
                    chat_restricted_users.restricted_at
                FROM chat_restricted_users
                LEFT JOIN users ON users.user_id = chat_restricted_users.user_id
                WHERE chat_restricted_users.chat_id = ?
                ORDER BY chat_restricted_users.restricted_at DESC
                """,
                (chat_id,),
            ).fetchall()

        return [
            ChatRestrictedUser(
                chat_id=row["chat_id"],
                user_id=row["user_id"],
                username=row["username"],
                display_name=row["display_name"],
                restricted_by_user_id=row["restricted_by_user_id"],
                restricted_at=row["restricted_at"],
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

    def try_record_daily_report(self, user_id: str, report_date: str, chat_id: str | None = None) -> bool:
        self.get_or_create_user(user_id)
        if chat_id is not None:
            chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO daily_user_reports (user_id, report_date, chat_id)
                VALUES (?, ?, ?)
                """,
                (user_id, report_date, chat_id),
            )
        return cursor.rowcount > 0

    def try_award_daily_galeraza(
        self,
        chat_id: str,
        game_date: str,
        user_id: str,
        message_id: str,
        message_date: str | None = None,
    ) -> bool:
        chat_id = self.resolve_chat_id(chat_id)
        self.get_or_create_user(user_id)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO galeraza_daily_winners (
                    chat_id,
                    game_date,
                    user_id,
                    message_id,
                    message_date
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (chat_id, game_date, user_id, message_id, message_date),
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

    def get_hisopo_intensity_percent(self, chat_id: str) -> int:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO hisopo_chat_settings (chat_id)
                VALUES (?)
                ON CONFLICT(chat_id) DO NOTHING
                """,
                (chat_id,),
            )
            row = conn.execute(
                "SELECT intensity_percent FROM hisopo_chat_settings WHERE chat_id = ?",
                (chat_id,),
            ).fetchone()
        return int(row["intensity_percent"])

    def set_hisopo_intensity_percent(self, chat_id: str, intensity_percent: int) -> None:
        if intensity_percent not in {1, 5, 10, 15, 20}:
            raise ValueError("La intensidad de Hisopos debe ser 1, 5, 10, 15 o 20.")
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO hisopo_chat_settings (chat_id, intensity_percent)
                VALUES (?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    intensity_percent = excluded.intensity_percent,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (chat_id, intensity_percent),
            )

    def save_hisopo_spawn(
        self,
        chat_id: str,
        message_id: str,
        hisopo_type: str,
        points: int,
        source: str,
        spawned_at: str,
        expires_at: str,
        appearance_type: str | None = None,
        required_helpers: int = 1,
    ) -> HisopoSpawn:
        if required_helpers < 1:
            raise ValueError("El Hisopo debe requerir al menos un participante.")
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO hisopo_spawns (
                    chat_id, message_id, hisopo_type, appearance_type, points,
                    required_helpers, source, spawned_at, expires_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chat_id,
                    message_id,
                    hisopo_type,
                    appearance_type or hisopo_type,
                    points,
                    required_helpers,
                    source,
                    spawned_at,
                    expires_at,
                ),
            )
            row = conn.execute(
                "SELECT * FROM hisopo_spawns WHERE chat_id = ? AND message_id = ?",
                (chat_id, message_id),
            ).fetchone()
        return _hisopo_spawn_from_row(row)

    def get_hisopo_spawn(self, chat_id: str, message_id: str) -> HisopoSpawn | None:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM hisopo_spawns WHERE chat_id = ? AND message_id = ?",
                (chat_id, message_id),
            ).fetchone()
        return _hisopo_spawn_from_row(row) if row is not None else None

    def list_active_hisopo_spawns(self) -> list[HisopoSpawn]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM hisopo_spawns WHERE status = 'active' ORDER BY expires_at"
            ).fetchall()
        return [_hisopo_spawn_from_row(row) for row in rows]

    def list_pending_hisopo_message_cleanups(
        self,
        chat_id: str,
    ) -> list[HisopoMessageCleanup]:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    chat_id,
                    message_id,
                    spawned_at,
                    message_cleanup_attempts,
                    message_cleanup_last_attempt_at
                FROM hisopo_spawns
                WHERE chat_id = ? AND message_cleanup_status = 'pending'
                ORDER BY spawned_at, message_id
                """,
                (chat_id,),
            ).fetchall()
        return [
            HisopoMessageCleanup(
                chat_id=row["chat_id"],
                message_id=row["message_id"],
                spawned_at=row["spawned_at"],
                attempts=row["message_cleanup_attempts"],
                last_attempt_at=row["message_cleanup_last_attempt_at"],
            )
            for row in rows
        ]

    def mark_hisopo_messages_deleted(
        self,
        chat_id: str,
        message_ids: Iterable[str],
        now: datetime,
    ) -> None:
        chat_id = self.resolve_chat_id(chat_id)
        now_text = now.isoformat()
        with self._connect() as conn:
            conn.executemany(
                """
                UPDATE hisopo_spawns
                SET
                    message_cleanup_status = 'deleted',
                    message_cleanup_last_attempt_at = ?,
                    message_deleted_at = ?,
                    message_cleanup_error = NULL
                WHERE chat_id = ? AND message_id = ?
                """,
                (
                    (now_text, now_text, chat_id, str(message_id))
                    for message_id in message_ids
                ),
            )

    def mark_hisopo_messages_cleanup_expired(
        self,
        chat_id: str,
        message_ids: Iterable[str],
        now: datetime,
        error: str,
    ) -> None:
        chat_id = self.resolve_chat_id(chat_id)
        now_text = now.isoformat()
        with self._connect() as conn:
            conn.executemany(
                """
                UPDATE hisopo_spawns
                SET
                    message_cleanup_status = 'expired',
                    message_cleanup_last_attempt_at = ?,
                    message_cleanup_error = ?
                WHERE chat_id = ? AND message_id = ?
                """,
                (
                    (now_text, error, chat_id, str(message_id))
                    for message_id in message_ids
                ),
            )

    def record_hisopo_message_cleanup_failure(
        self,
        chat_id: str,
        message_ids: Iterable[str],
        now: datetime,
        error: str,
        max_attempts: int,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("La limpieza de Hisopos debe admitir al menos un intento.")
        chat_id = self.resolve_chat_id(chat_id)
        now_text = now.isoformat()
        with self._connect() as conn:
            conn.executemany(
                """
                UPDATE hisopo_spawns
                SET
                    message_cleanup_attempts = message_cleanup_attempts + 1,
                    message_cleanup_status = CASE
                        WHEN message_cleanup_attempts + 1 >= ? THEN 'failed'
                        ELSE 'pending'
                    END,
                    message_cleanup_last_attempt_at = ?,
                    message_cleanup_error = ?
                WHERE chat_id = ? AND message_id = ?
                """,
                (
                    (max_attempts, now_text, error, chat_id, str(message_id))
                    for message_id in message_ids
                ),
            )

    def capture_hisopo(
        self,
        chat_id: str,
        message_id: str,
        user_id: str,
        now: datetime,
        next_scheduled_for: datetime | Iterable[datetime],
        points_at_capture: int | None = None,
    ) -> HisopoCaptureResult:
        chat_id = self.resolve_chat_id(chat_id)
        self.get_or_create_user(user_id)
        now_text = now.isoformat()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM hisopo_spawns WHERE chat_id = ? AND message_id = ?",
                (chat_id, message_id),
            ).fetchone()
            if row is None:
                return HisopoCaptureResult("missing", None)

            spawn = _hisopo_spawn_from_row(row)
            if spawn.status == "captured":
                return HisopoCaptureResult("taken", spawn)
            if spawn.status == "rotten":
                return HisopoCaptureResult("rotten", spawn)
            if now >= datetime.fromisoformat(spawn.expires_at):
                conn.execute(
                    """
                    UPDATE hisopo_spawns
                    SET status = 'rotten'
                    WHERE chat_id = ? AND message_id = ? AND status = 'active'
                    """,
                    (chat_id, message_id),
                )
                return HisopoCaptureResult(
                    "rotten",
                    _hisopo_spawn_from_row(row, status="rotten"),
                )

            if spawn.hisopo_type == "miracle":
                leader_row = conn.execute(
                    "SELECT MAX(points) AS points FROM hisopo_scores WHERE chat_id = ?",
                    (chat_id,),
                ).fetchone()
                leader_points = int(leader_row["points"] or 0)
                awarded_points = max(15, (leader_points + 1) // 2)
            else:
                awarded_points = (
                    spawn.points if points_at_capture is None else points_at_capture
                )

            conn.execute(
                """
                UPDATE hisopo_spawns
                SET status = 'captured', winner_user_id = ?, captured_at = ?, points = ?
                WHERE chat_id = ? AND message_id = ? AND status = 'active'
                """,
                (user_id, now_text, awarded_points, chat_id, message_id),
            )
            conn.execute(
                """
                INSERT INTO hisopo_scores (chat_id, user_id, points)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id, user_id) DO UPDATE SET
                    points = hisopo_scores.points + excluded.points,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (chat_id, user_id, awarded_points),
            )
            if not (
                spawn.hisopo_type == "fleeting"
                and spawn.appearance_type == "mystery"
                and awarded_points == 0
            ):
                _increment_hisopo_collection(
                    conn,
                    chat_id,
                    user_id,
                    spawn.hisopo_type,
                    now_text,
                )
            scheduled_datetimes = (
                (next_scheduled_for,)
                if isinstance(next_scheduled_for, datetime)
                else tuple(next_scheduled_for)
            )
            schedules = []
            for scheduled_for in scheduled_datetimes:
                schedule = _insert_hisopo_schedule_below_daily_cap(
                    conn,
                    chat_id,
                    scheduled_for,
                    message_id,
                )
                if schedule is not None:
                    schedules.append(schedule)
            captured_spawn = _hisopo_spawn_from_row(
                row,
                status="captured",
                winner_user_id=user_id,
                captured_at=now_text,
                points=awarded_points,
            )
        return HisopoCaptureResult(
            "captured",
            captured_spawn,
            schedules[0] if schedules else None,
            tuple(schedules[1:]),
        )

    def contribute_to_giant_hisopo(
        self,
        chat_id: str,
        message_id: str,
        user_id: str,
        now: datetime,
        next_scheduled_for: datetime,
    ) -> HisopoGiantContributionResult:
        chat_id = self.resolve_chat_id(chat_id)
        self.get_or_create_user(user_id)
        now_text = now.isoformat()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM hisopo_spawns WHERE chat_id = ? AND message_id = ?",
                (chat_id, message_id),
            ).fetchone()
            if row is None:
                return HisopoGiantContributionResult("missing", None)

            spawn = _hisopo_spawn_from_row(row)
            if spawn.status == "captured":
                return HisopoGiantContributionResult("taken", spawn)
            if spawn.status == "rotten":
                return HisopoGiantContributionResult("rotten", spawn)
            if spawn.hisopo_type != "giant":
                return HisopoGiantContributionResult("invalid", spawn)
            if now >= datetime.fromisoformat(spawn.expires_at):
                conn.execute(
                    """
                    UPDATE hisopo_spawns
                    SET status = 'rotten'
                    WHERE chat_id = ? AND message_id = ? AND status = 'active'
                    """,
                    (chat_id, message_id),
                )
                return HisopoGiantContributionResult(
                    "rotten",
                    _hisopo_spawn_from_row(row, status="rotten"),
                )

            existing = conn.execute(
                """
                SELECT 1 FROM hisopo_giant_contributions
                WHERE chat_id = ? AND message_id = ? AND user_id = ?
                """,
                (chat_id, message_id, user_id),
            ).fetchone()
            if existing is not None:
                participants = _giant_participant_ids(conn, chat_id, message_id)
                return HisopoGiantContributionResult(
                    "already_joined",
                    spawn,
                    participants,
                    len(participants),
                    spawn.required_helpers,
                )

            conn.execute(
                """
                INSERT INTO hisopo_giant_contributions (
                    chat_id, message_id, user_id, contributed_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (chat_id, message_id, user_id, now_text),
            )
            revealed = spawn.appearance_type != "giant"
            if revealed:
                conn.execute(
                    """
                    UPDATE hisopo_spawns
                    SET appearance_type = 'giant'
                    WHERE chat_id = ? AND message_id = ?
                    """,
                    (chat_id, message_id),
                )
                spawn = _hisopo_spawn_from_row(row, appearance_type="giant")

            participants = _giant_participant_ids(conn, chat_id, message_id)
            contribution_count = len(participants)
            if contribution_count < spawn.required_helpers:
                return HisopoGiantContributionResult(
                    "joined",
                    spawn,
                    participants,
                    contribution_count,
                    spawn.required_helpers,
                    revealed=revealed,
                )

            conn.execute(
                """
                UPDATE hisopo_spawns
                SET status = 'captured', winner_user_id = ?, captured_at = ?,
                    appearance_type = 'giant'
                WHERE chat_id = ? AND message_id = ? AND status = 'active'
                """,
                (user_id, now_text, chat_id, message_id),
            )
            for participant_user_id in participants:
                conn.execute(
                    """
                    INSERT INTO hisopo_scores (chat_id, user_id, points)
                    VALUES (?, ?, ?)
                    ON CONFLICT(chat_id, user_id) DO UPDATE SET
                        points = hisopo_scores.points + excluded.points,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (chat_id, participant_user_id, spawn.points),
                )
                _increment_hisopo_collection(
                    conn,
                    chat_id,
                    participant_user_id,
                    spawn.hisopo_type,
                    now_text,
                )
            schedule = _insert_hisopo_schedule_below_daily_cap(
                conn,
                chat_id,
                next_scheduled_for,
                message_id,
            )
            completed_spawn = _hisopo_spawn_from_row(
                row,
                status="captured",
                winner_user_id=user_id,
                captured_at=now_text,
                appearance_type="giant",
            )
        return HisopoGiantContributionResult(
            "completed",
            completed_spawn,
            participants,
            contribution_count,
            completed_spawn.required_helpers,
            schedule,
            revealed,
        )

    def get_giant_contribution_count(self, chat_id: str, message_id: str) -> int:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM hisopo_giant_contributions
                WHERE chat_id = ? AND message_id = ?
                """,
                (chat_id, message_id),
            ).fetchone()
        return int(row["total"])

    def mark_hisopo_rotten(self, chat_id: str, message_id: str, now: datetime) -> bool:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT status, expires_at FROM hisopo_spawns WHERE chat_id = ? AND message_id = ?",
                (chat_id, message_id),
            ).fetchone()
            if (
                row is None
                or row["status"] != "active"
                or now < datetime.fromisoformat(row["expires_at"])
            ):
                return False
            conn.execute(
                """
                UPDATE hisopo_spawns
                SET status = 'rotten'
                WHERE chat_id = ? AND message_id = ? AND status = 'active'
                """,
                (chat_id, message_id),
            )
        return True

    def get_hisopo_scores(self, chat_id: str) -> list[HisopoScore]:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    hisopo_scores.user_id,
                    users.username,
                    users.display_name,
                    hisopo_scores.points
                FROM hisopo_scores
                LEFT JOIN users ON users.user_id = hisopo_scores.user_id
                WHERE hisopo_scores.chat_id = ?
                ORDER BY hisopo_scores.points DESC,
                    lower(COALESCE(users.display_name, users.username, hisopo_scores.user_id)) ASC
                """,
                (chat_id,),
            ).fetchall()
        return [
            HisopoScore(
                user_id=row["user_id"],
                username=row["username"],
                display_name=row["display_name"],
                points=row["points"],
            )
            for row in rows
        ]

    def get_hisopo_collection(
        self,
        chat_id: str,
        user_id: str,
    ) -> list[HisopoCollectionEntry]:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT hisopo_type, capture_count, first_captured_at, last_captured_at
                FROM hisopo_collections
                WHERE chat_id = ? AND user_id = ?
                ORDER BY first_captured_at, hisopo_type
                """,
                (chat_id, user_id),
            ).fetchall()
        return [
            HisopoCollectionEntry(
                hisopo_type=row["hisopo_type"],
                capture_count=row["capture_count"],
                first_captured_at=row["first_captured_at"],
                last_captured_at=row["last_captured_at"],
            )
            for row in rows
        ]

    def reset_processing_hisopo_schedules(self) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE hisopo_schedules SET status = 'pending' WHERE status = 'processing'"
            )

    def list_pending_hisopo_schedules(self) -> list[HisopoSchedule]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT schedule_id, chat_id, scheduled_for, status, source_message_id
                FROM hisopo_schedules
                WHERE status = 'pending'
                ORDER BY scheduled_for, schedule_id
                """
            ).fetchall()
        return [_hisopo_schedule_from_row(row) for row in rows]

    def claim_hisopo_schedule(self, schedule_id: int) -> HisopoSchedule | None:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                """
                UPDATE hisopo_schedules
                SET status = 'processing'
                WHERE schedule_id = ? AND status = 'pending'
                """,
                (schedule_id,),
            )
            if cursor.rowcount == 0:
                return None
            row = conn.execute(
                """
                SELECT schedule_id, chat_id, scheduled_for, status, source_message_id
                FROM hisopo_schedules
                WHERE schedule_id = ?
                """,
                (schedule_id,),
            ).fetchone()
        return _hisopo_schedule_from_row(row)

    def complete_hisopo_schedule(self, schedule_id: int, status: str) -> None:
        if status not in {"sent", "failed", "cancelled"}:
            raise ValueError("Estado final de programacion de Hisopos invalido.")
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE hisopo_schedules
                SET status = ?, completed_at = CURRENT_TIMESTAMP
                WHERE schedule_id = ?
                """,
                (status, schedule_id),
            )

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

    def save_restart_confirmation(
        self,
        chat_id: str,
        message_id: str,
        requester_user_id: str,
    ) -> None:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO restart_confirmations (chat_id, message_id, requester_user_id)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id, message_id) DO UPDATE SET
                    requester_user_id = excluded.requester_user_id,
                    created_at = CURRENT_TIMESTAMP
                """,
                (chat_id, message_id, requester_user_id),
            )

    def get_restart_confirmation(self, chat_id: str, message_id: str) -> RestartConfirmation | None:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT chat_id, message_id, requester_user_id, created_at
                FROM restart_confirmations
                WHERE chat_id = ? AND message_id = ?
                """,
                (chat_id, message_id),
            ).fetchone()
        if row is None:
            return None
        return RestartConfirmation(
            chat_id=row["chat_id"],
            message_id=row["message_id"],
            requester_user_id=row["requester_user_id"],
            created_at=row["created_at"],
        )

    def list_restart_confirmations_before(self, cutoff: str) -> list[RestartConfirmation]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT chat_id, message_id, requester_user_id, created_at
                FROM restart_confirmations
                WHERE created_at < ?
                ORDER BY created_at ASC
                """,
                (cutoff,),
            ).fetchall()
        return [
            RestartConfirmation(
                chat_id=row["chat_id"],
                message_id=row["message_id"],
                requester_user_id=row["requester_user_id"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def delete_restart_confirmation(self, chat_id: str, message_id: str) -> None:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM restart_confirmations WHERE chat_id = ? AND message_id = ?",
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

    def add_trigger(
        self,
        chat_id: str,
        trigger_name: str,
        display_name: str,
        text: str | None,
        media_type: str | None,
        file_id: str | None,
        caption: str | None,
        created_by_user_id: str,
        payload_json: str | None = None,
    ) -> bool:
        chat_id = self.resolve_chat_id(chat_id)
        self.get_or_create_user(created_by_user_id)
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO triggers (
                    chat_id,
                    trigger_name,
                    display_name,
                    text,
                    media_type,
                    file_id,
                    caption,
                    payload_json,
                    created_by_user_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chat_id,
                    trigger_name,
                    display_name,
                    text,
                    media_type,
                    file_id,
                    caption,
                    payload_json,
                    created_by_user_id,
                ),
            )
        return cursor.rowcount > 0

    def delete_trigger(self, chat_id: str, trigger_name: str) -> bool:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM triggers WHERE chat_id = ? AND trigger_name = ?",
                (chat_id, trigger_name),
            )
        return cursor.rowcount > 0

    def get_trigger(self, chat_id: str, trigger_name: str) -> Trigger | None:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT chat_id, trigger_name, display_name, text, media_type, file_id, caption, payload_json, created_by_user_id, created_at
                FROM triggers
                WHERE chat_id = ? AND trigger_name = ?
                """,
                (chat_id, trigger_name),
            ).fetchone()
        return _trigger_from_row(row) if row is not None else None

    def list_triggers(self, chat_id: str) -> list[Trigger]:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT chat_id, trigger_name, display_name, text, media_type, file_id, caption, payload_json, created_by_user_id, created_at
                FROM triggers
                WHERE chat_id = ?
                ORDER BY lower(display_name) ASC
                """,
                (chat_id,),
            ).fetchall()
        return [_trigger_from_row(row) for row in rows]

    def play_russian_roulette(
        self,
        chat_id: str,
        user_id: str,
        *,
        bullet_position: int | None = None,
    ) -> RussianRouletteShot:
        if bullet_position is not None and not 0 <= bullet_position <= 5:
            raise ValueError("bullet_position must be between 0 and 5")

        chat_id = self.resolve_chat_id(chat_id)
        self.get_or_create_user(user_id)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT bullet_position, shots_fired
                FROM russian_roulette_states
                WHERE chat_id = ? AND user_id = ?
                """,
                (chat_id, user_id),
            ).fetchone()

            if row is None:
                selected_position = secrets.randbelow(6) if bullet_position is None else bullet_position
                shots_fired = 0
                conn.execute(
                    """
                    INSERT INTO russian_roulette_states (
                        chat_id,
                        user_id,
                        bullet_position,
                        shots_fired
                    )
                    VALUES (?, ?, ?, 0)
                    """,
                    (chat_id, user_id, selected_position),
                )
            else:
                selected_position = row["bullet_position"]
                shots_fired = row["shots_fired"]

            if shots_fired == selected_position:
                conn.execute(
                    "DELETE FROM russian_roulette_states WHERE chat_id = ? AND user_id = ?",
                    (chat_id, user_id),
                )
                return RussianRouletteShot(hit=True, remaining_shots=0)

            next_shot = shots_fired + 1
            conn.execute(
                """
                UPDATE russian_roulette_states
                SET shots_fired = ?, updated_at = CURRENT_TIMESTAMP
                WHERE chat_id = ? AND user_id = ?
                """,
                (next_shot, chat_id, user_id),
            )
            return RussianRouletteShot(hit=False, remaining_shots=6 - next_shot)

    def add_expense(
        self,
        chat_id: str,
        user_id: str,
        amount_cents: int,
        currency: str,
        payment_method: str,
        source: str,
        description: str,
    ) -> Expense:
        chat_id = self.resolve_chat_id(chat_id)
        self.get_or_create_user(user_id)
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO expenses (
                    chat_id,
                    user_id,
                    amount_cents,
                    currency,
                    payment_method,
                    source,
                    description
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chat_id,
                    user_id,
                    amount_cents,
                    currency,
                    payment_method,
                    source,
                    description,
                ),
            )
            row = conn.execute(
                """
                SELECT
                    expenses.expense_id,
                    expenses.chat_id,
                    expenses.user_id,
                    users.username,
                    users.display_name,
                    expenses.amount_cents,
                    expenses.currency,
                    expenses.payment_method,
                    expenses.source,
                    expenses.description,
                    expenses.sheet_status,
                    expenses.sheet_error,
                    expenses.created_at,
                    expenses.synced_at
                FROM expenses
                LEFT JOIN users ON users.user_id = expenses.user_id
                WHERE expenses.expense_id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
        return _expense_from_row(row)

    def mark_expense_synced(self, expense_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE expenses
                SET
                    sheet_status = 'synced',
                    sheet_error = NULL,
                    synced_at = CURRENT_TIMESTAMP
                WHERE expense_id = ?
                """,
                (expense_id,),
            )

    def mark_expense_failed(self, expense_id: int, error: str | None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE expenses
                SET
                    sheet_status = 'pending',
                    sheet_error = ?,
                    synced_at = NULL
                WHERE expense_id = ?
                """,
                (error, expense_id),
            )

    def list_recent_expenses(self, chat_id: str, limit: int = 20) -> list[Expense]:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    expenses.expense_id,
                    expenses.chat_id,
                    expenses.user_id,
                    users.username,
                    users.display_name,
                    expenses.amount_cents,
                    expenses.currency,
                    expenses.payment_method,
                    expenses.source,
                    expenses.description,
                    expenses.sheet_status,
                    expenses.sheet_error,
                    expenses.created_at,
                    expenses.synced_at
                FROM expenses
                LEFT JOIN users ON users.user_id = expenses.user_id
                WHERE expenses.chat_id = ?
                ORDER BY expenses.expense_id DESC
                LIMIT ?
                """,
                (chat_id, limit),
            ).fetchall()
        return [_expense_from_row(row) for row in rows]

    def list_pending_expenses(self, chat_id: str, limit: int = 200) -> list[Expense]:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    expenses.expense_id,
                    expenses.chat_id,
                    expenses.user_id,
                    users.username,
                    users.display_name,
                    expenses.amount_cents,
                    expenses.currency,
                    expenses.payment_method,
                    expenses.source,
                    expenses.description,
                    expenses.sheet_status,
                    expenses.sheet_error,
                    expenses.created_at,
                    expenses.synced_at
                FROM expenses
                LEFT JOIN users ON users.user_id = expenses.user_id
                WHERE expenses.chat_id = ? AND expenses.sheet_status != 'synced'
                ORDER BY expenses.expense_id ASC
                LIMIT ?
                """,
                (chat_id, limit),
            ).fetchall()
        return [_expense_from_row(row) for row in rows]

    def count_pending_expenses(self, chat_id: str) -> int:
        chat_id = self.resolve_chat_id(chat_id)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS pending_count
                FROM expenses
                WHERE chat_id = ? AND sheet_status != 'synced'
                """,
                (chat_id,),
            ).fetchone()
        return int(row["pending_count"]) if row is not None else 0


def _normalize_username(username: str | None) -> str | None:
    if not username:
        return None
    return username.removeprefix("@").strip() or None


def _trigger_from_row(row: sqlite3.Row) -> Trigger:
    return Trigger(
        chat_id=row["chat_id"],
        trigger_name=row["trigger_name"],
        display_name=row["display_name"],
        text=row["text"],
        media_type=row["media_type"],
        file_id=row["file_id"],
        caption=row["caption"],
        created_by_user_id=row["created_by_user_id"],
        created_at=row["created_at"],
        payload_json=row["payload_json"],
    )


def _expense_from_row(row: sqlite3.Row) -> Expense:
    return Expense(
        expense_id=row["expense_id"],
        chat_id=row["chat_id"],
        user_id=row["user_id"],
        username=row["username"],
        display_name=row["display_name"],
        amount_cents=row["amount_cents"],
        currency=row["currency"],
        payment_method=row["payment_method"],
        source=row["source"],
        description=row["description"],
        sheet_status=row["sheet_status"],
        sheet_error=row["sheet_error"],
        created_at=row["created_at"],
        synced_at=row["synced_at"],
    )


def _hisopo_spawn_from_row(
    row: sqlite3.Row,
    *,
    status: str | None = None,
    winner_user_id: str | None = None,
    captured_at: str | None = None,
    points: int | None = None,
    appearance_type: str | None = None,
) -> HisopoSpawn:
    return HisopoSpawn(
        chat_id=row["chat_id"],
        message_id=row["message_id"],
        hisopo_type=row["hisopo_type"],
        appearance_type=appearance_type
        or (
            row["appearance_type"]
            if "appearance_type" in row.keys() and row["appearance_type"] is not None
            else row["hisopo_type"]
        ),
        points=points if points is not None else row["points"],
        required_helpers=(
            row["required_helpers"]
            if "required_helpers" in row.keys() and row["required_helpers"] is not None
            else 1
        ),
        source=row["source"],
        spawned_at=row["spawned_at"],
        expires_at=row["expires_at"],
        status=status or row["status"],
        winner_user_id=winner_user_id if winner_user_id is not None else row["winner_user_id"],
        captured_at=captured_at if captured_at is not None else row["captured_at"],
    )


def _giant_participant_ids(
    conn: sqlite3.Connection,
    chat_id: str,
    message_id: str,
) -> tuple[str, ...]:
    rows = conn.execute(
        """
        SELECT user_id
        FROM hisopo_giant_contributions
        WHERE chat_id = ? AND message_id = ?
        ORDER BY contributed_at, user_id
        """,
        (chat_id, message_id),
    ).fetchall()
    return tuple(str(row["user_id"]) for row in rows)


def _increment_hisopo_collection(
    conn: sqlite3.Connection,
    chat_id: str,
    user_id: str,
    hisopo_type: str,
    captured_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO hisopo_collections (
            chat_id, user_id, hisopo_type, capture_count,
            first_captured_at, last_captured_at
        )
        VALUES (?, ?, ?, 1, ?, ?)
        ON CONFLICT(chat_id, user_id, hisopo_type) DO UPDATE SET
            capture_count = hisopo_collections.capture_count + 1,
            first_captured_at = MIN(hisopo_collections.first_captured_at, excluded.first_captured_at),
            last_captured_at = MAX(hisopo_collections.last_captured_at, excluded.last_captured_at)
        """,
        (chat_id, user_id, hisopo_type, captured_at, captured_at),
    )


def _hisopo_schedule_from_row(row: sqlite3.Row) -> HisopoSchedule:
    return HisopoSchedule(
        schedule_id=row["schedule_id"],
        chat_id=row["chat_id"],
        scheduled_for=row["scheduled_for"],
        status=row["status"],
        source_message_id=row["source_message_id"],
    )


def _insert_hisopo_schedule_below_daily_cap(
    conn: sqlite3.Connection,
    chat_id: str,
    scheduled_for: datetime,
    source_message_id: str,
) -> HisopoSchedule | None:
    """Insert a next-day spawn unless this chat already filled that Argentine day."""
    target_day = _argentina_calendar_day(scheduled_for)
    scheduled_rows = conn.execute(
        "SELECT scheduled_for FROM hisopo_schedules WHERE chat_id = ?",
        (chat_id,),
    ).fetchall()
    scheduled_count = sum(
        _argentina_calendar_day(datetime.fromisoformat(row["scheduled_for"]))
        == target_day
        for row in scheduled_rows
    )
    if scheduled_count >= MAX_HISOPO_SCHEDULES_PER_CHAT_DAY:
        return None

    scheduled_text = scheduled_for.isoformat()
    cursor = conn.execute(
        """
        INSERT INTO hisopo_schedules (
            chat_id, scheduled_for, source_message_id
        )
        VALUES (?, ?, ?)
        """,
        (chat_id, scheduled_text, source_message_id),
    )
    return HisopoSchedule(
        schedule_id=int(cursor.lastrowid),
        chat_id=chat_id,
        scheduled_for=scheduled_text,
        status="pending",
        source_message_id=source_message_id,
    )


def _argentina_calendar_day(value: datetime) -> date:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(_ARGENTINA_TIMEZONE).date()


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
