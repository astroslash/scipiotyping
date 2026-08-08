import pytest

from scipiotyping.scoring import calculate_score, compare_text, score_text


def test_standard_score():
    result = calculate_score(250, 245, 5, 60)
    assert result == {"gross_wpm": 50.0, "net_wpm": 45.0, "accuracy": 98.0}


def test_zero_characters():
    assert calculate_score(0, 0, 0, 10)["accuracy"] == 0


def test_invalid_duration():
    with pytest.raises(ValueError): calculate_score(10, 10, 0, 0)


def test_compare_text_tracks_expected_keys():
    matches, errors, keys = compare_text("abc de", "abx de")
    assert (matches, errors, keys) == (5, 1, {"c": 1})


def test_compare_text_counts_missing_space():
    _, errors, keys = compare_text("a b", "a")
    assert errors == 2 and keys["space"] == 1 and keys["b"] == 1


def test_completed_text():
    result = score_text("hello", "hello", 12)
    assert result["completed"] is True and result["errors"] == 0 and result["accuracy"] == 100


def test_unicode_text():
    result = score_text("Odysseus—ready", "Odysseus—ready", 20)
    assert result["completed"] and result["typed_characters"] == 14

