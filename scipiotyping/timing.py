from __future__ import annotations

from datetime import UTC, datetime, time, timedelta, tzinfo


def local_day_bounds(now: datetime | None = None, local_zone: tzinfo | None = None) -> tuple[datetime, datetime]:
    """Return UTC boundaries for the current day in the computer's local zone."""
    current = now or datetime.now().astimezone()
    local_current = current.astimezone(local_zone) if local_zone else current.astimezone()
    if local_zone:
        start_local = datetime.combine(local_current.date(), time.min, tzinfo=local_zone)
        end_local = datetime.combine(local_current.date() + timedelta(days=1), time.min, tzinfo=local_zone)
    else:
        # astimezone() on separate naive midnights asks the operating system for
        # the correct local offset on each date, including DST transitions.
        start_local = datetime.combine(local_current.date(), time.min).astimezone()
        end_local = datetime.combine(local_current.date() + timedelta(days=1), time.min).astimezone()
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def daily_practice_summary(connection, profile_id: int, goal_minutes: int,
                           now: datetime | None = None, local_zone: tzinfo | None = None) -> dict:
    start, end = local_day_bounds(now, local_zone)
    seconds = connection.execute(
        """SELECT COALESCE(SUM(practice_time_segments.active_seconds),0)
           FROM practice_time_segments
           JOIN practice_sessions ON practice_sessions.id=practice_time_segments.session_id
           WHERE practice_sessions.profile_id=?
             AND practice_time_segments.recorded_at>=?
             AND practice_time_segments.recorded_at<?""",
        (profile_id, start.isoformat(), end.isoformat()),
    ).fetchone()[0]
    active = max(0.0, float(seconds or 0))
    goal = max(1, int(goal_minutes)) * 60
    return {
        "active_seconds": round(active, 1),
        "goal_seconds": goal,
        "remaining_seconds": round(max(0.0, goal - active), 1),
        "percentage": round(min(100.0, active / goal * 100), 1),
        "goal_reached": active >= goal,
    }


def format_duration(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"
