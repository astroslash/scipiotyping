import json
from datetime import date, timedelta

from scipiotyping.lessons import lesson_passages, placement_level, progression_level, unlocked_lessons
from scipiotyping.progress import aggregate_key_stats, focus_keys, key_report, streak_days, weak_keys
from scipiotyping.targeted import targeted_passage


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
    assert len(lesson_passages()) == 14
    assert sum(bool(item.get("young_reader")) for item in unlocked_lessons(1)) == 6
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


def test_key_report_ranks_weak_keys_and_detects_mastery():
    weak = {"a": {"expected": 20, "matched": 15, "errors": 5}}
    mastered = {"s": {"expected": 35, "matched": 34, "errors": 1}}
    rows = [{"key_stats": json.dumps({**weak, **mastered})}]
    totals = aggregate_key_stats(rows)
    assert totals["a"]["expected"] == 20
    report = {item["key"]: item for item in key_report(rows)}
    assert report["a"]["status"] == "weak"
    assert report["s"]["status"] == "mastered"
    assert focus_keys(rows)[0]["key"] == "a"


def test_incomplete_attempts_do_not_affect_key_analysis():
    rows = [
        {"completed": 0, "key_stats": json.dumps({"a": {"expected": 100, "matched": 0, "errors": 100}})},
        {"completed": 1, "key_stats": json.dumps({"a": {"expected": 10, "matched": 10, "errors": 0}})},
    ]
    assert aggregate_key_stats(rows)["a"] == {"expected": 10, "matched": 10, "errors": 0}


def test_targeted_drill_is_deterministic_and_emphasizes_focus_keys():
    sources = [item["text"] for item in lesson_passages()]
    first = targeted_passage(7, ["a", "s"], sources, date(2026, 8, 8))
    second = targeted_passage(7, ["s", "a"], sources, date(2026, 8, 8))
    assert first["id"] == second["id"] and first["text"] == second["text"]
    assert first["generator_version"] == 1
    assert all(first["text"].lower().count(key) >= 8 for key in ("a", "s"))
