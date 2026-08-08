import pytest

from scipiotyping.scoring import (align_text, alignment_summary,
                                  calculate_score, completion_threshold,
                                  score_text)


def test_legacy_standard_score():
    result = calculate_score(250, 245, 5, 60)
    assert result == {"gross_wpm": 50.0, "net_wpm": 45.0, "accuracy": 98.0}


def test_zero_characters():
    assert calculate_score(0, 0, 0, 10)["accuracy"] == 0


def test_invalid_duration():
    with pytest.raises(ValueError):
        calculate_score(10, 10, 0, 0)
    with pytest.raises(ValueError):
        score_text("target", "typed", 0)


def test_missing_space_does_not_shift_remainder():
    summary = alignment_summary("The army moved east.", "Thearmy moved east.")
    assert summary["deletions"] == 1
    assert summary["substitutions"] == summary["insertions"] == 0
    assert summary["matches"] == len("Thearmy moved east.")
    assert summary["error_map"] == {"space": 1}


def test_missing_letter_does_not_shift_remainder():
    summary = alignment_summary("Odysseus sailed home.", "Odyseus sailed home.")
    assert summary["deletions"] == 1 and summary["matches"] == len("Odyseus sailed home.")


def test_insertion_and_substitution_are_distinguished():
    inserted = alignment_summary("abc", "abxc")
    substituted = alignment_summary("abc", "abx")
    assert inserted["insertions"] == 1 and inserted["matches"] == 3
    assert substituted["substitutions"] == 1 and substituted["matches"] == 2


def test_adjacent_reversal_is_one_transposition():
    summary = alignment_summary("form", "from")
    assert summary["transpositions"] == 1
    assert summary["substitutions"] == 0
    assert summary["matches"] == 2


def test_repeated_words_align_usefully():
    summary = alignment_summary("the line and the line", "the line the line")
    assert summary["deletions"] == 4
    assert summary["matches"] == len("the line the line")


def test_adjusted_wpm_counts_only_aligned_matches():
    result = score_text("abcdefghij", "abcdxfghij", 60)
    assert result["gross_wpm"] == 2.0
    assert result["adjusted_wpm"] == result["net_wpm"] == 1.8
    assert result["substitutions"] == 1
    assert result["accuracy"] == 90.0
    assert result["completed"] is True


def test_near_complete_text_is_eligible_for_manual_finish():
    target = "a" * 100
    result = score_text(target, "a" * completion_threshold(len(target)), 60)
    assert result["completed"] is True and result["deletions"] == 15


def test_short_partial_text_is_not_complete():
    assert score_text("abcdefghij", "abc", 10)["completed"] is False


def test_unicode_text():
    result = score_text("Odysseus—ready", "Odysseus—ready", 20)
    assert result["completed"] and result["typed_characters"] == 14


def test_alignment_operations_reconstruct_both_inputs():
    target, typed = "a bc", "axb c"
    operations = align_text(target, typed)
    assert "".join(operation["expected"] for operation in operations) == target
    assert "".join(operation["typed"] for operation in operations) == typed


def test_key_statistics_record_opportunities_matches_and_errors():
    score = score_text("a sad", "a sxad", 60)
    assert score["key_stats"]["a"]["expected"] == 2
    assert score["key_stats"]["a"]["matched"] == 2
    assert score["key_stats"]["d"]["errors"] == 0
    assert score["key_stats"]["extra x"]["errors"] == 1
