import sqlite3

from scipiotyping.db import SCHEMA_V1, migrate


def test_v1_database_migrates_without_data_loss(tmp_path):
    connection=sqlite3.connect(tmp_path/"old.db"); connection.row_factory=sqlite3.Row
    connection.executescript(SCHEMA_V1)
    connection.execute("INSERT INTO profiles(name,created_at) VALUES('Kenneth','2026-01-01')")
    connection.commit(); migrate(connection)
    assert connection.execute("SELECT name FROM profiles").fetchone()[0]=="Kenneth"
    assert connection.execute("SELECT version FROM schema_version").fetchone()[0]==3
    assert connection.execute("SELECT name FROM sqlite_master WHERE name='custom_passages'").fetchone()
    connection.close()

