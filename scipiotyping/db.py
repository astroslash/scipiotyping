from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
import json

import click
from flask import current_app, g


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


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        path = Path(current_app.config["DATABASE"])
        path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


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
    connection.commit()


def init_database() -> None:
    connection = get_db()
    connection.executescript(SCHEMA_V1)
    migrate(connection)
    connection.execute(
        "INSERT OR IGNORE INTO profiles(name, created_at) VALUES (?, ?)",
        ("Kenneth", datetime.now(UTC).isoformat()),
    )
    connection.commit()


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


@click.command("init-db")
def init_db_command() -> None:
    init_database()
    click.echo("Initialized and migrated the ScipioTyping database.")


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
