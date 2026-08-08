from datetime import UTC, datetime, timedelta, timezone

from scipiotyping.db import get_db
from scipiotyping.timing import daily_practice_summary, format_duration, local_day_bounds


def test_local_day_bounds_respect_denver_midnight():
    zone = timezone(timedelta(hours=-6), "MDT")
    start, end = local_day_bounds(datetime(2026, 7, 4, 12, tzinfo=zone), zone)
    assert start == datetime(2026, 7, 4, 6, tzinfo=UTC)
    assert end == datetime(2026, 7, 5, 6, tzinfo=UTC)


def test_daily_summary_separates_days_profiles_and_goal_states(app):
    zone = timezone(timedelta(hours=-6), "MDT")
    now = datetime(2026, 7, 4, 12, tzinfo=zone)
    with app.app_context():
        connection = get_db()
        connection.execute("INSERT INTO profiles(name,created_at) VALUES('Alex','2026-01-01')")
        alex = connection.execute("SELECT id FROM profiles WHERE name='Alex'").fetchone()[0]
        rows = [
            ("today-1", 1, "p", "practice", "2026-07-04T06:00:00+00:00", 500),
            ("today-2", 1, "p", "practice", "2026-07-05T05:59:59+00:00", 450),
            ("yesterday", 1, "p", "practice", "2026-07-04T05:59:59+00:00", 800),
            ("other-profile", alex, "p", "practice", "2026-07-04T12:00:00+00:00", 800),
        ]
        connection.executemany("""INSERT INTO practice_sessions(
            id,profile_id,passage_id,mode,started_at,updated_at,active_seconds)
            VALUES(?,?,?,?,?,?,?)""", [row[:5] + (row[4], row[5]) for row in rows])
        connection.executemany("""INSERT INTO practice_time_segments(session_id,recorded_at,active_seconds)
            VALUES(?,?,?)""", [(row[0], row[4], row[5]) for row in rows])
        connection.commit()
        summary = daily_practice_summary(connection, 1, 15, now, zone)
    assert summary["active_seconds"] == 950
    assert summary["goal_reached"] is True and summary["remaining_seconds"] == 0
    assert summary["percentage"] == 100


def test_session_time_can_span_two_local_days(app):
    zone = timezone(timedelta(hours=-6), "MDT")
    with app.app_context():
        connection = get_db()
        connection.execute("""INSERT INTO practice_sessions(
            id,profile_id,passage_id,mode,started_at,updated_at,active_seconds)
            VALUES('midnight',1,'p','practice','2026-07-05T05:59:00+00:00','2026-07-05T06:01:00+00:00',120)""")
        connection.executemany("INSERT INTO practice_time_segments(session_id,recorded_at,active_seconds) VALUES(?,?,?)", [
            ("midnight", "2026-07-05T05:59:30+00:00", 60),
            ("midnight", "2026-07-05T06:00:30+00:00", 60),
        ])
        connection.commit()
        july_four = daily_practice_summary(connection, 1, 15, datetime(2026, 7, 4, 23, 59, tzinfo=zone), zone)
        july_five = daily_practice_summary(connection, 1, 15, datetime(2026, 7, 5, 0, 1, tzinfo=zone), zone)
    assert july_four["active_seconds"] == 60
    assert july_five["active_seconds"] == 60


def test_duration_formatting():
    assert format_duration(522.9) == "8:42"
    assert format_duration(3661) == "1:01:01"
