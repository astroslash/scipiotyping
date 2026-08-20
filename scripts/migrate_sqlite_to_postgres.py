"""Copy a ScipioTyping SQLite database into an empty hosted PostgreSQL database."""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

from scipiotyping import create_app
from scipiotyping.db import get_db, is_postgres


DATA_TABLES = (
    "attempts",
    "achievements",
    "custom_passages",
    "practice_sessions",
    "practice_time_segments",
)
SERIAL_TABLES = ("profiles", "attempts", "achievements", "practice_time_segments")


def source_rows(connection: sqlite3.Connection, table: str) -> tuple[list[str], list[sqlite3.Row]]:
    columns = [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
    return columns, connection.execute(f"SELECT * FROM {table}").fetchall()


def insert_rows(destination, table: str, columns: list[str], rows: list[sqlite3.Row]) -> None:
    if not rows:
        return
    placeholders = ",".join("?" for _ in columns)
    destination.executemany(
        f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})",
        [tuple(row[column] for column in columns) for row in rows],
    )


def migrate(source_path: Path) -> dict[str, int]:
    if not source_path.is_file():
        raise RuntimeError(f"SQLite source does not exist: {source_path}")
    if not os.environ.get("DATABASE_URL", "").startswith(("postgres://", "postgresql://")):
        raise RuntimeError("Set DATABASE_URL to the destination PostgreSQL connection string.")

    source = sqlite3.connect(source_path)
    source.row_factory = sqlite3.Row
    try:
        integrity = source.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {integrity}")
        required = {"profiles", "attempts", "achievements", "settings", "custom_passages",
                    "practice_sessions", "practice_time_segments"}
        available = {row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not required.issubset(available):
            raise RuntimeError("The source is not a current ScipioTyping database. Start v1.5 or later locally once first.")

        app = create_app()
        with app.app_context():
            destination = get_db()
            if not is_postgres(destination):
                raise RuntimeError("The destination is not PostgreSQL.")
            populated = sum(destination.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                            for table in DATA_TABLES)
            if populated:
                raise RuntimeError("The destination already contains progress data; migration was stopped.")

            source_profiles = source.execute("SELECT id,name FROM profiles ORDER BY id").fetchall()
            target_profiles = destination.execute("SELECT id,name FROM profiles ORDER BY id").fetchall()
            target_by_name = {row["name"]: row["id"] for row in target_profiles}
            if any(target_by_name.get(row["name"]) != row["id"] for row in source_profiles):
                raise RuntimeError("Profile IDs do not align with the destination; migration was stopped safely.")

            counts: dict[str, int] = {}
            try:
                profile_columns, profile_rows = source_rows(source, "profiles")
                profile_columns = [column for column in profile_columns if column != "pin_hash"]
                for row in profile_rows:
                    assignments = ",".join(f"{column}=?" for column in profile_columns if column != "id")
                    values = [row[column] for column in profile_columns if column != "id"] + [row["id"]]
                    destination.execute(f"UPDATE profiles SET {assignments} WHERE id=?", values)
                counts["profiles"] = len(profile_rows)

                for table in DATA_TABLES:
                    columns, rows = source_rows(source, table)
                    insert_rows(destination, table, columns, rows)
                    counts[table] = len(rows)

                setting_rows = source.execute(
                    "SELECT key,value FROM settings WHERE key <> 'parent_pin_hash'"
                ).fetchall()
                insert_rows(destination, "settings", ["key", "value"], setting_rows)
                counts["settings"] = len(setting_rows)

                for table in SERIAL_TABLES:
                    destination.execute(
                        f"SELECT setval(pg_get_serial_sequence('{table}','id'), "
                        f"GREATEST(COALESCE(MAX(id),1),1), MAX(id) IS NOT NULL) FROM {table}"
                    )
                destination.commit()
            except Exception:
                destination.rollback()
                raise
            return counts
    finally:
        source.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", default="instance/scipiotyping.db",
                        help="path to the local SQLite database")
    arguments = parser.parse_args()
    try:
        counts = migrate(Path(arguments.source).resolve())
    except Exception as error:
        print(f"Migration stopped: {error}", file=sys.stderr)
        return 1
    print("Migration complete: " + ", ".join(f"{name}={count}" for name, count in counts.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
