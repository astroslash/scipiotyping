from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import click
from flask import current_app, g


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS profiles (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL,
  daily_goal_minutes INTEGER NOT NULL DEFAULT 15, preferred_difficulty INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS attempts (
  id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  passage_id TEXT NOT NULL, started_at TEXT NOT NULL, completed_at TEXT NOT NULL,
  duration_seconds REAL NOT NULL CHECK(duration_seconds > 0), typed_characters INTEGER NOT NULL,
  correct_characters INTEGER NOT NULL, errors INTEGER NOT NULL, corrected_errors INTEGER NOT NULL DEFAULT 0,
  gross_wpm REAL NOT NULL, net_wpm REAL NOT NULL, accuracy REAL NOT NULL,
  completed INTEGER NOT NULL DEFAULT 1, error_map TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS achievements (
  id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
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


def init_database() -> None:
    connection = get_db()
    connection.executescript(SCHEMA)
    connection.execute(
        "INSERT OR IGNORE INTO profiles(name, created_at) VALUES (?, ?)",
        ("Kenneth", datetime.now(UTC).isoformat()),
    )
    connection.commit()


@click.command("init-db")
def init_db_command() -> None:
    init_database()
    click.echo("Initialized the ScipioTyping database.")


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

