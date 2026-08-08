import json
from datetime import date, timedelta

from scipiotyping.lessons import lesson_passages, placement_level, progression_level, unlocked_lessons
from scipiotyping.progress import streak_days, weak_keys


def test_placement_boundaries():
    assert placement_level(45, 98) == 5
    assert placement_level(30, 95) == 4
    assert placement_level(20, 92) == 3
    assert placement_level(12, 88) == 2
    assert placement_level(50, 80) == 1


def test_unlocks_only_at_or_below_level():
    lessons = unlocked_lessons(2)
    assert all(item["unlocked"] == (item["level"] <= 2) for item in lessons)


def test_focused_drills_and_progression():
    assert len(lesson_passages()) == 8
    assert progression_level(1, {"home-row", "upper-row"}) == 2
    assert progression_level(1, {"home-row"}) == 1


def test_streak_includes_today_and_consecutive_days():
    rows=[{"completed_at":(date.today()-timedelta(days=n)).isoformat()} for n in range(3)]
    assert streak_days(rows) == 3


def test_streak_allows_today_to_be_empty():
    rows=[{"completed_at":(date.today()-timedelta(days=1)).isoformat()}]
    assert streak_days(rows) == 1


def test_weak_keys_handles_bad_and_valid_maps():
    rows=[{"error_map":json.dumps({"a":3,"space":1})},{"error_map":"bad"}]
    assert weak_keys(rows)[0] == ("a",3)
