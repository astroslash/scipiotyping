from __future__ import annotations

from collections.abc import Iterator, Mapping
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click
from flask import current_app, g
from werkzeug.security import check_password_hash, generate_password_hash

SCHEMA_VERSION = 8
SEEDED_PROFILES = ("Kenneth", "William", "Alice", "Emily")

SCHEMA_V1 = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS profiles (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL,
  daily_goal_minutes INTEGER NOT NULL DEFAULT 15,
  preferred_difficulty INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS attempts (
  id INTEGER PRIMARY KEY,
  profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  passage_id TEXT NOT NULL, started_at TEXT NOT NULL, completed_at TEXT NOT NULL,
  duration_seconds REAL NOT NULL CHECK(duration_seconds > 0),
  typed_characters INTEGER NOT NULL, correct_characters INTEGER NOT NULL,
  errors INTEGER NOT NULL, corrected_errors INTEGER NOT NULL DEFAULT 0,
  gross_wpm REAL NOT NULL, net_wpm REAL NOT NULL, accuracy REAL NOT NULL,
  completed INTEGER NOT NULL DEFAULT 1, error_map TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS achievements (
  id INTEGER PRIMARY KEY,
  profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  code TEXT NOT NULL, earned_at TEXT NOT NULL, UNIQUE(profile_id, code)
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
INSERT INTO schema_version(version) SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM schema_version);
"""

POSTGRES_SCHEMA = (
    """CREATE TABLE IF NOT EXISTS profiles (
      id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL,
      daily_goal_minutes INTEGER NOT NULL DEFAULT 15,
      preferred_difficulty INTEGER NOT NULL DEFAULT 1,
      placement_level INTEGER,
      placement_complete INTEGER NOT NULL DEFAULT 0,
      active INTEGER NOT NULL DEFAULT 1,
      pin_hash TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS attempts (
      id BIGSERIAL PRIMARY KEY,
      profile_id BIGINT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
      passage_id TEXT NOT NULL, started_at TEXT NOT NULL, completed_at TEXT NOT NULL,
      duration_seconds DOUBLE PRECISION NOT NULL CHECK(duration_seconds > 0),
      typed_characters INTEGER NOT NULL, correct_characters INTEGER NOT NULL,
      errors INTEGER NOT NULL, corrected_errors INTEGER NOT NULL DEFAULT 0,
      gross_wpm DOUBLE PRECISION NOT NULL, net_wpm DOUBLE PRECISION NOT NULL,
      accuracy DOUBLE PRECISION NOT NULL, completed INTEGER NOT NULL DEFAULT 1,
      error_map TEXT NOT NULL DEFAULT '{}', mode TEXT NOT NULL DEFAULT 'practice',
      lesson_id TEXT, adjusted_wpm DOUBLE PRECISION,
      substitutions INTEGER NOT NULL DEFAULT 0, insertions INTEGER NOT NULL DEFAULT 0,
      deletions INTEGER NOT NULL DEFAULT 0, transpositions INTEGER NOT NULL DEFAULT 0,
      key_stats TEXT NOT NULL DEFAULT '{}', target_text TEXT,
      focus_keys TEXT NOT NULL DEFAULT '[]', generator_version INTEGER,
      passage_revision INTEGER
    )""",
    """CREATE TABLE IF NOT EXISTS achievements (
      id BIGSERIAL PRIMARY KEY,
      profile_id BIGINT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
      code TEXT NOT NULL, earned_at TEXT NOT NULL, UNIQUE(profile_id, code)
    )""",
    "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
    """CREATE TABLE IF NOT EXISTS custom_passages (
      id TEXT PRIMARY KEY, title TEXT NOT NULL, text TEXT NOT NULL,
      category TEXT NOT NULL, difficulty INTEGER NOT NULL CHECK(difficulty BETWEEN 1 AND 5),
      age INTEGER NOT NULL, objectives TEXT NOT NULL, context TEXT NOT NULL,
      vocabulary TEXT NOT NULL, source TEXT NOT NULL,
      rights TEXT NOT NULL DEFAULT 'original', created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS practice_sessions (
      id TEXT PRIMARY KEY,
      profile_id BIGINT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
      passage_id TEXT NOT NULL, mode TEXT NOT NULL, started_at TEXT NOT NULL,
      updated_at TEXT NOT NULL, completed_at TEXT,
      active_seconds DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK(active_seconds >= 0),
      attempt_id BIGINT UNIQUE REFERENCES attempts(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS practice_time_segments (
      id BIGSERIAL PRIMARY KEY,
      session_id TEXT NOT NULL REFERENCES practice_sessions(id) ON DELETE CASCADE,
      recorded_at TEXT NOT NULL,
      active_seconds DOUBLE PRECISION NOT NULL CHECK(active_seconds > 0)
    )""",
    "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)",
    "CREATE INDEX IF NOT EXISTS idx_attempts_profile_date ON attempts(profile_id, completed_at)",
    "CREATE INDEX IF NOT EXISTS idx_practice_sessions_profile_started ON practice_sessions(profile_id, started_at)",
    "CREATE INDEX IF NOT EXISTS idx_practice_time_segments_recorded ON practice_time_segments(recorded_at)",
)


def get_db() -> sqlite3.Connection | PostgresConnection:
    if "db" not in g:
        database_url = current_app.config.get("DATABASE_URL", "")
        if database_url.startswith(("postgres://", "postgresql://")):
            g.db = PostgresConnection(database_url)
        else:
            path = Path(current_app.config["DATABASE"])
            path.parent.mkdir(parents=True, exist_ok=True)
            g.db = sqlite3.connect(path)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


class HybridRow(Mapping[str, Any]):
    """A psycopg row with sqlite.Row-compatible name and position lookup."""

    def __init__(self, columns: tuple[str, ...], values: tuple[Any, ...]):
        self._columns = columns
        self._values = values
        self._mapping = dict(zip(columns, values, strict=True))

    def __getitem__(self, key: str | int) -> Any:
        return self._values[key] if isinstance(key, int) else self._mapping[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._columns)

    def __len__(self) -> int:
        return len(self._columns)


def _hybrid_row_factory(cursor):
    columns = tuple(column.name for column in (cursor.description or ()))
    return lambda values: HybridRow(columns, values)


class PostgresConnection:
    """Small compatibility layer for the app's existing parameterized SQL."""

    backend = "postgresql"

    def __init__(self, database_url: str):
        import psycopg

        self._connection = psycopg.connect(database_url, row_factory=_hybrid_row_factory)

    @staticmethod
    def _sql(statement: str) -> str:
        return statement.replace("?", "%s")

    def execute(self, statement: str, parameters: tuple | list = ()):
        return self._connection.execute(self._sql(statement), parameters)

    def executemany(self, statement: str, parameters):
        return self._connection.executemany(self._sql(statement), parameters)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()


def is_postgres(connection=None) -> bool:
    connection = connection or get_db()
    return getattr(connection, "backend", "sqlite") == "postgresql"


def integrity_errors() -> tuple[type[Exception], ...]:
    try:
        import psycopg
        return (sqlite3.IntegrityError, psycopg.IntegrityError)
    except ImportError:
        return (sqlite3.IntegrityError,)


def close_db(_error=None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def _has_column(connection: sqlite3.Connection, table: str, column: str) -> bool:
    return any(row[1] == column for row in connection.execute(f"PRAGMA table_info({table})"))


def migrate(connection: sqlite3.Connection) -> None:
    """Upgrade in place; each operation is safe when startup is repeated."""
    version = connection.execute("SELECT version FROM schema_version").fetchone()[0]
    if version < 2:
        additions = {
            "profiles": [("placement_level", "INTEGER"), ("placement_complete", "INTEGER NOT NULL DEFAULT 0")],
            "attempts": [("mode", "TEXT NOT NULL DEFAULT 'practice'"), ("lesson_id", "TEXT")],
        }
        for table, columns in additions.items():
            for name, definition in columns:
                if not _has_column(connection, table, name):
                    connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS custom_passages (
          id TEXT PRIMARY KEY, title TEXT NOT NULL, text TEXT NOT NULL,
          category TEXT NOT NULL, difficulty INTEGER NOT NULL CHECK(difficulty BETWEEN 1 AND 5),
          age INTEGER NOT NULL, objectives TEXT NOT NULL, context TEXT NOT NULL,
          vocabulary TEXT NOT NULL, source TEXT NOT NULL, rights TEXT NOT NULL DEFAULT 'original',
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_attempts_profile_date ON attempts(profile_id, completed_at);
        """)
        connection.execute("UPDATE schema_version SET version=2")
        version = 2
    if version < 3:
        if not _has_column(connection, "profiles", "active"):
            connection.execute("ALTER TABLE profiles ADD COLUMN active INTEGER NOT NULL DEFAULT 1")
        connection.execute("UPDATE schema_version SET version=3")
        version = 3
    if version < 4:
        additions = [
            ("adjusted_wpm", "REAL"),
            ("substitutions", "INTEGER NOT NULL DEFAULT 0"),
            ("insertions", "INTEGER NOT NULL DEFAULT 0"),
            ("deletions", "INTEGER NOT NULL DEFAULT 0"),
            ("transpositions", "INTEGER NOT NULL DEFAULT 0"),
        ]
        for name, definition in additions:
            if not _has_column(connection, "attempts", name):
                connection.execute(f"ALTER TABLE attempts ADD COLUMN {name} {definition}")
        connection.execute("UPDATE attempts SET adjusted_wpm=net_wpm WHERE adjusted_wpm IS NULL")
        connection.execute("UPDATE schema_version SET version=4")
        version = 4
    if version < 5:
        additions = [
            ("key_stats", "TEXT NOT NULL DEFAULT '{}'"),
            ("target_text", "TEXT"),
            ("focus_keys", "TEXT NOT NULL DEFAULT '[]'"),
            ("generator_version", "INTEGER"),
        ]
        for name, definition in additions:
            if not _has_column(connection, "attempts", name):
                connection.execute(f"ALTER TABLE attempts ADD COLUMN {name} {definition}")
        connection.execute("UPDATE schema_version SET version=5")
        version = 5
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS practice_sessions (
      id TEXT PRIMARY KEY,
      profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
      passage_id TEXT NOT NULL,
      mode TEXT NOT NULL,
      started_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      completed_at TEXT,
      active_seconds REAL NOT NULL DEFAULT 0 CHECK(active_seconds >= 0),
      attempt_id INTEGER UNIQUE REFERENCES attempts(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_practice_sessions_profile_started
      ON practice_sessions(profile_id, started_at);
    CREATE TABLE IF NOT EXISTS practice_time_segments (
      id INTEGER PRIMARY KEY,
      session_id TEXT NOT NULL REFERENCES practice_sessions(id) ON DELETE CASCADE,
      recorded_at TEXT NOT NULL,
      active_seconds REAL NOT NULL CHECK(active_seconds > 0)
    );
    CREATE INDEX IF NOT EXISTS idx_practice_time_segments_recorded
      ON practice_time_segments(recorded_at);
    """)
    if version < 6:
        connection.execute("UPDATE schema_version SET version=6")
        version = 6
    if version < 7:
        if not _has_column(connection, "attempts", "passage_revision"):
            connection.execute("ALTER TABLE attempts ADD COLUMN passage_revision INTEGER")
        connection.execute("UPDATE schema_version SET version=7")
        version = 7
    if version < 8:
        if not _has_column(connection, "profiles", "pin_hash"):
            connection.execute("ALTER TABLE profiles ADD COLUMN pin_hash TEXT")
        connection.execute("UPDATE schema_version SET version=8")
    connection.commit()


def init_postgres(connection: PostgresConnection) -> None:
    for statement in POSTGRES_SCHEMA:
        connection.execute(statement)
    version_row = connection.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    if version_row is None:
        connection.execute("INSERT INTO schema_version(version) VALUES(?)", (SCHEMA_VERSION,))
    elif version_row[0] < SCHEMA_VERSION:
        connection.execute("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS pin_hash TEXT")
        connection.execute("UPDATE schema_version SET version=?", (SCHEMA_VERSION,))
    connection.commit()


def seed_profile_pins(connection) -> None:
    configured = current_app.config.get("SEED_PROFILE_PINS", {})
    for name, pin in configured.items():
        row = connection.execute("SELECT id,pin_hash FROM profiles WHERE name=?", (name,)).fetchone()
        if row and (not row["pin_hash"] or not check_password_hash(row["pin_hash"], pin)):
            connection.execute(
                "UPDATE profiles SET pin_hash=? WHERE id=?",
                (generate_password_hash(pin), row["id"]),
            )
    connection.commit()


def init_database() -> None:
    connection = get_db()
    if is_postgres(connection):
        init_postgres(connection)
    else:
        connection.executescript(SCHEMA_V1)
        migrate(connection)
    for name in SEEDED_PROFILES:
        daily_goal = 10 if name == "Emily" else 15
        if is_postgres(connection):
            connection.execute(
                "INSERT INTO profiles(name,created_at,daily_goal_minutes,preferred_difficulty) "
                "VALUES(?,?,?,1) ON CONFLICT(name) DO NOTHING",
                (name, datetime.now(UTC).isoformat(), daily_goal),
            )
        else:
            connection.execute(
                "INSERT OR IGNORE INTO profiles(name,created_at,daily_goal_minutes,preferred_difficulty) "
                "VALUES(?,?,?,1)",
                (name, datetime.now(UTC).isoformat(), daily_goal),
            )
    connection.commit()
    seed_profile_pins(connection)


def backfill_key_stats(connection: sqlite3.Connection, passage_lookup: dict[str, str]) -> None:
    """Add best-effort key evidence to pre-v5 attempts whose target still exists."""
    rows = connection.execute("SELECT id, passage_id, error_map FROM attempts WHERE key_stats='{}'").fetchall()
    for row in rows:
        target = passage_lookup.get(row["passage_id"])
        if not target:
            continue
        try:
            errors = json.loads(row["error_map"] or "{}")
        except (json.JSONDecodeError, TypeError):
            errors = {}
        statistics: dict[str, dict[str, int]] = {}
        for character in target:
            key = "space" if character == " " else character.lower()
            statistics.setdefault(key, {"expected": 0, "matched": 0, "errors": 0})["expected"] += 1
        for key, values in statistics.items():
            try:
                count = min(values["expected"], max(0, int(errors.get(key, 0))))
            except (TypeError, ValueError):
                count = 0
            values["errors"] = count
            values["matched"] = values["expected"] - count
        connection.execute("UPDATE attempts SET key_stats=? WHERE id=?", (json.dumps(statistics), row["id"]))
    connection.commit()


def backfill_attempt_content(connection: sqlite3.Connection, passage_lookup: dict[str, dict]) -> None:
    """Preserve the exact target and revision for historical attempts when known."""
    rows = connection.execute(
        "SELECT id, passage_id, target_text, passage_revision FROM attempts "
        "WHERE target_text IS NULL OR passage_revision IS NULL"
    ).fetchall()
    for row in rows:
        passage = passage_lookup.get(row["passage_id"])
        if not passage:
            continue
        connection.execute(
            "UPDATE attempts SET target_text=COALESCE(target_text, ?), "
            "passage_revision=COALESCE(passage_revision, ?) WHERE id=?",
            (passage["text"], int(passage.get("revision", passage.get("generator_version", 1))), row["id"]),
        )
    connection.commit()


def backfill_practice_sessions(connection: sqlite3.Connection) -> None:
    """Represent historical attempts as completed sessions exactly once."""
    if is_postgres(connection):
        connection.execute("""INSERT INTO practice_sessions(
            id, profile_id, passage_id, mode, started_at, updated_at, completed_at,
            active_seconds, attempt_id)
            SELECT 'legacy-' || id, profile_id, passage_id, mode, started_at,
                   completed_at, completed_at, duration_seconds, id FROM attempts
            ON CONFLICT DO NOTHING""")
    else:
        connection.execute("""INSERT OR IGNORE INTO practice_sessions(
            id, profile_id, passage_id, mode, started_at, updated_at, completed_at,
            active_seconds, attempt_id)
            SELECT 'legacy-' || id, profile_id, passage_id, mode, started_at,
                   completed_at, completed_at, duration_seconds, id FROM attempts""")
    connection.execute("""INSERT INTO practice_time_segments(session_id,recorded_at,active_seconds)
        SELECT practice_sessions.id, practice_sessions.completed_at, practice_sessions.active_seconds
        FROM practice_sessions
        WHERE practice_sessions.completed_at IS NOT NULL
          AND practice_sessions.active_seconds > 0
          AND NOT EXISTS (SELECT 1 FROM practice_time_segments
                          WHERE practice_time_segments.session_id=practice_sessions.id)""")
    connection.commit()


@click.command("init-db")
def init_db_command() -> None:
    init_database()
    click.echo("Initialized and migrated the ScipioTyping database.")


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
