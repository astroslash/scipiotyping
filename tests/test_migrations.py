import sqlite3

import json

from scipiotyping.db import SCHEMA_V1, backfill_key_stats, backfill_practice_sessions, migrate


def test_v1_database_migrates_without_data_loss(tmp_path):
    connection=sqlite3.connect(tmp_path/"old.db"); connection.row_factory=sqlite3.Row
    connection.executescript(SCHEMA_V1)
    connection.execute("INSERT INTO profiles(name,created_at) VALUES('Kenneth','2026-01-01')")
    connection.commit(); migrate(connection)
    assert connection.execute("SELECT name FROM profiles").fetchone()[0]=="Kenneth"
    assert connection.execute("SELECT version FROM schema_version").fetchone()[0]==6
    assert connection.execute("SELECT name FROM sqlite_master WHERE name='custom_passages'").fetchone()
    columns={row[1] for row in connection.execute("PRAGMA table_info(attempts)")}
    assert {"adjusted_wpm","substitutions","insertions","deletions","transpositions",
            "key_stats","target_text","focus_keys","generator_version"}.issubset(columns)
    assert connection.execute("SELECT name FROM sqlite_master WHERE name='practice_sessions'").fetchone()
    assert connection.execute("SELECT name FROM sqlite_master WHERE name='practice_time_segments'").fetchone()
    connection.close()


def test_schema_five_backfills_known_targets_and_leaves_unknown_targets(tmp_path):
    connection = sqlite3.connect(tmp_path / "history.db")
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA_V1)
    connection.execute("INSERT INTO profiles(name,created_at) VALUES('Kenneth','2026-01-01')")
    attempt = (1, "known", "2026-01-01", "2026-01-01", 60, 5, 4, 1, 0, 1, 1, 80, 1, '{\"a\":1}')
    connection.execute("""INSERT INTO attempts(profile_id,passage_id,started_at,completed_at,duration_seconds,
        typed_characters,correct_characters,errors,corrected_errors,gross_wpm,net_wpm,accuracy,completed,error_map)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", attempt)
    connection.execute("""INSERT INTO attempts(profile_id,passage_id,started_at,completed_at,duration_seconds,
        typed_characters,correct_characters,errors,corrected_errors,gross_wpm,net_wpm,accuracy,completed,error_map)
        VALUES(1,'missing','2026-01-01','2026-01-01',60,5,5,0,0,1,1,100,1,'{}')""")
    connection.commit()
    migrate(connection)
    backfill_key_stats(connection, {"known": "a sad"})
    backfill_practice_sessions(connection)
    known = json.loads(connection.execute("SELECT key_stats FROM attempts WHERE passage_id='known'").fetchone()[0])
    unknown = connection.execute("SELECT key_stats FROM attempts WHERE passage_id='missing'").fetchone()[0]
    assert known["a"] == {"expected": 2, "matched": 1, "errors": 1}
    assert unknown == "{}"
    sessions = connection.execute("SELECT * FROM practice_sessions ORDER BY attempt_id").fetchall()
    assert len(sessions) == 2 and sessions[0]["active_seconds"] == 60
    assert connection.execute("SELECT COUNT(*) FROM practice_time_segments").fetchone()[0] == 2
    backfill_practice_sessions(connection)
    assert connection.execute("SELECT COUNT(*) FROM practice_sessions").fetchone()[0] == 2
    assert connection.execute("SELECT COUNT(*) FROM practice_time_segments").fetchone()[0] == 2
    connection.close()


def test_schema_six_repairs_missing_session_tables(tmp_path):
    connection = sqlite3.connect(tmp_path / "partial.db")
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA_V1)
    migrate(connection)
    connection.execute("DROP TABLE practice_time_segments")
    connection.commit()
    assert connection.execute("SELECT version FROM schema_version").fetchone()[0] == 6
    migrate(connection)
    assert connection.execute("SELECT name FROM sqlite_master WHERE name='practice_time_segments'").fetchone()
    connection.close()
