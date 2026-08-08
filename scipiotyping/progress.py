from __future__ import annotations

import json
from collections import Counter
from datetime import date, timedelta

ACHIEVEMENTS = {
    "first-passage": ("First Expedition", "Complete your first passage."),
    "accuracy-95": ("Steady Hands", "Complete a passage with at least 95% accuracy."),
    "accuracy-100": ("Perfect Copy", "Complete a passage with 100% accuracy."),
    "speed-25": ("Swift Scribe", "Reach 25 net WPM."),
    "ten-passages": ("Ten Expeditions", "Complete ten passages."),
    "five-subjects": ("Curious Scholar", "Practice in five subjects."),
}


def award_achievements(connection, profile_id: int, passage_lookup: dict[str, dict]) -> list[str]:
    rows = connection.execute("SELECT * FROM attempts WHERE profile_id=? AND completed=1", (profile_id,)).fetchall()
    codes: set[str] = set()
    if rows: codes.add("first-passage")
    if any(row["accuracy"] >= 95 for row in rows): codes.add("accuracy-95")
    if any(row["accuracy"] >= 100 for row in rows): codes.add("accuracy-100")
    if any(row["net_wpm"] >= 25 for row in rows): codes.add("speed-25")
    if len(rows) >= 10: codes.add("ten-passages")
    categories = {passage_lookup[row["passage_id"]]["category"] for row in rows if row["passage_id"] in passage_lookup}
    if len(categories) >= 5: codes.add("five-subjects")
    existing = {row[0] for row in connection.execute("SELECT code FROM achievements WHERE profile_id=?", (profile_id,))}
    new = sorted(codes - existing)
    connection.executemany(
        "INSERT INTO achievements(profile_id, code, earned_at) VALUES(?,?,datetime('now'))",
        [(profile_id, code) for code in new],
    )
    return new


def streak_days(rows) -> int:
    practiced = {date.fromisoformat(row["completed_at"][:10]) for row in rows}
    if not practiced: return 0
    cursor = date.today()
    if cursor not in practiced:
        cursor -= timedelta(days=1)
    streak = 0
    while cursor in practiced:
        streak += 1; cursor -= timedelta(days=1)
    return streak


def weak_keys(rows, limit: int = 6) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    for row in rows:
        try: counts.update(json.loads(row["error_map"] or "{}"))
        except (json.JSONDecodeError, TypeError): pass
    return counts.most_common(limit)


def recommend(profile, rows, all_passages: list[dict]) -> tuple[dict, str]:
    level = profile["placement_level"] or profile["preferred_difficulty"] or 1
    recent_ids = {row["passage_id"] for row in rows[:8]}
    candidates = [p for p in all_passages if p["difficulty"] == level and p["id"] not in recent_ids]
    if not candidates: candidates = [p for p in all_passages if p["difficulty"] <= level]
    weak = weak_keys(rows, 3)
    pool = candidates or all_passages
    if weak:
        weak_chars = [" " if key == "space" else key for key, _ in weak]
        chosen = max(pool, key=lambda p: (sum(p["text"].lower().count(key.lower()) for key in weak_chars), -p["difficulty"]))
    else:
        chosen = sorted(pool, key=lambda p: (p["difficulty"], p["title"]))[0]
    if not rows: reason = "Start with a short passage while ScipioTyping learns your pace."
    elif weak: reason = "Recommended at your level; slow down around: " + ", ".join(k for k, _ in weak) + "."
    else: reason = "Recommended at your current level to build steady accuracy."
    return chosen, reason
