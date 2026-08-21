import json
from collections import Counter
from pathlib import Path

import pytest

from scipiotyping.content import (content_report, load_passages,
                                   render_inventory, validate_passages)


def _passage(identifier: str, title: str | None = None) -> dict:
    return {
        "id": identifier,
        "title": title or identifier.replace("-", " ").title(),
        "text": (f"{identifier} offers a careful educational explanation for typing practice. "
                 "It includes enough words to test the scalable content loader without using external services. "
                 "Students can work accurately and learn from the passage at the same time."),
        "category": "Test",
        "difficulty": 2,
        "age": 10,
        "objectives": ["clear explanation"],
        "context": "Synthetic test content.",
        "vocabulary": [],
        "source": "Original test passage",
        "rights": "original",
        "typing_focus": ["accuracy"],
        "reading_level": 5,
        "revision": 1,
        "added_in": "1.3.0",
        "review_status": "reviewed",
        "reviewed_on": "2026-08-09",
        "references": [{"citation": "Original test passage"}],
    }


def test_builtin_library_preserves_all_released_passages(app):
    items = load_passages(app.config["CONTENT_PATH"])
    manifest = json.loads((Path(app.config["CONTENT_PATH"]) / "manifest.json").read_text(encoding="utf-8"))
    counts = {}
    for item in items:
        counts[item["category"]] = counts.get(item["category"], 0) + 1
    assert len(items) == 170 and counts == {
        "Animals": 10,
        "Battles and Strategy": 14,
        "Chess": 14,
        "Classical History": 14,
        "Epic Literature": 14,
        "Greek Mythology": 14,
        "History of Warfare": 14,
        "Kid Jokes": 10,
        "Leaders": 14,
        "Mathematics": 14,
        "Poetry": 14,
        "Silly Stories": 10,
        "World History": 14,
    }
    assert set(manifest["legacy_ids"]) == {item["id"] for item in items}


def test_young_reader_collection_is_simple_varied_and_age_appropriate(app):
    additions = [
        item for item in load_passages(app.config["CONTENT_PATH"])
        if item["added_in"] == "1.8.0"
    ]
    assert len(additions) == 30
    assert Counter(item["category"] for item in additions) == {
        "Animals": 10, "Kid Jokes": 10, "Silly Stories": 10,
    }
    assert all(item["difficulty"] == 1 and item["reading_level"] == 3 for item in additions)
    assert all(item["school_level"] == "elementary" for item in additions)
    assert all(item["age"] in {7, 8} and 35 <= item["word_count"] <= 55 for item in additions)
    assert all(item["rights"] == "original" and item["review_status"] == "reviewed"
               for item in additions)


def test_middle_school_library_excludes_the_grade_three_collection(app):
    items = load_passages(app.config["CONTENT_PATH"])
    middle = [item for item in items if item["school_level"] == "middle"]
    assert len(middle) == 140
    assert all(item["reading_level"] > 3 for item in middle)


def test_v110_long_reads_are_balanced_substantial_and_middle_school_only(app):
    additions = [
        item for item in load_passages(app.config["CONTENT_PATH"])
        if item["added_in"] == "1.10.0"
    ]
    advanced_categories = {
        "Battles and Strategy", "Chess", "Classical History", "Epic Literature",
        "Greek Mythology", "History of Warfare", "Leaders", "Mathematics",
        "Poetry", "World History",
    }
    assert len(additions) == 20
    assert Counter(item["category"] for item in additions) == {
        category: 2 for category in advanced_categories
    }
    assert Counter(item["difficulty"] for item in additions) == {4: 10, 5: 10}
    assert all(item["school_level"] == "middle" for item in additions)
    assert all(item["reading_level"] in {7, 8} for item in additions)
    assert all(175 <= item["word_count"] <= 215 for item in additions)
    assert all(item["character_count"] >= 1100 for item in additions)
    assert all(item["rights"] == "original" and item["review_status"] == "reviewed"
               for item in additions)
    assert all(item["references"][0].get("url", "").startswith("https://")
               for item in additions)


def test_v14_expansion_has_planned_levels_lengths_and_sources(app):
    additions = [
        item for item in load_passages(app.config["CONTENT_PATH"])
        if item["added_in"] == "1.4.0"
    ]
    bands = {2: (45, 65), 3: (60, 85), 4: (80, 115), 5: (105, 150)}
    assert len(additions) == 60
    assert Counter(item["difficulty"] for item in additions) == {
        2: 5, 3: 15, 4: 25, 5: 15,
    }
    for item in additions:
        low, high = bands[item["difficulty"]]
        assert low <= item["word_count"] <= high
        assert item["rights"] == "original"
        assert item["review_status"] == "reviewed"
        assert item["references"][0].get("url", "").startswith("https://")


def test_all_builtin_content_has_schema_two_metadata(app):
    for item in load_passages(app.config["CONTENT_PATH"]):
        assert item["context"] and item["source"] and item["typing_focus"]
        assert isinstance(item["vocabulary"], list) and item["review_status"] == "reviewed"
        assert item["references"] and item["revision"] >= 1
        assert 3 <= item["reading_level"] <= 10 and item["estimated_minutes"] >= 1


def test_duplicate_and_short_content_rejected():
    item = _passage("same-id")
    item["text"] = "short"
    errors = validate_passages([item, dict(item)])
    assert any("Duplicate" in error for error in errors)
    assert any("80" in error for error in errors)


def test_bad_rights_and_unreviewed_builtin_rejected():
    item = _passage("valid-id")
    item["rights"] = "copyrighted"
    item["review_status"] = "draft"
    errors = validate_passages([item], strict=True)
    assert any("rights" in error for error in errors)
    assert any("reviewed" in error for error in errors)


def test_directory_loader_detects_cross_file_duplicates(tmp_path):
    (tmp_path / "passages").mkdir()
    for name in ("one", "two"):
        (tmp_path / "passages" / f"{name}.json").write_text(
            json.dumps([_passage("same-id")]), encoding="utf-8")
    (tmp_path / "manifest.json").write_text(json.dumps({
        "schema_version": 2,
        "files": ["passages/one.json", "passages/two.json"],
        "legacy_ids": ["same-id"],
    }), encoding="utf-8")
    load_passages.cache_clear()
    with pytest.raises(ValueError, match="Duplicate id"):
        load_passages(str(tmp_path))
    load_passages.cache_clear()


def test_loader_handles_five_hundred_passages(tmp_path):
    path = tmp_path / "large.json"
    path.write_text(json.dumps([_passage(f"item-{number}") for number in range(500)]), encoding="utf-8")
    load_passages.cache_clear()
    assert len(load_passages(str(path))) == 500
    load_passages.cache_clear()


def test_content_report_and_inventory_are_deterministic(app):
    items = load_passages(app.config["CONTENT_PATH"])
    report = content_report(items)
    inventory = render_inventory(items)
    assert report["total"] == len(items)
    assert sum(report["categories"].values()) == len(items)
    assert "# Content inventory" in inventory and "| Chess | 14 |" in inventory
