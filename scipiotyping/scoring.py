from __future__ import annotations

from collections import Counter


def compare_text(target: str, typed: str) -> tuple[int, int, dict[str, int]]:
    """Return matching positions, uncorrected errors, and expected-key errors."""
    matches = sum(a == b for a, b in zip(target, typed))
    errors = sum(a != b for a, b in zip(target, typed)) + abs(len(target) - len(typed))
    key_errors: Counter[str] = Counter()
    for index, expected in enumerate(target):
        if index >= len(typed) or typed[index] != expected:
            key_errors[expected if expected != " " else "space"] += 1
    return matches, errors, dict(key_errors)


def calculate_score(
    typed_characters: int, correct_characters: int, errors: int, seconds: float
) -> dict[str, float]:
    if seconds <= 0:
        raise ValueError("Duration must be positive.")
    typed_characters = max(0, int(typed_characters))
    correct_characters = max(0, min(int(correct_characters), typed_characters))
    errors = max(0, int(errors))
    minutes = seconds / 60
    gross = typed_characters / 5 / minutes
    net = max(0.0, gross - errors / minutes)
    accuracy = correct_characters / typed_characters * 100 if typed_characters else 0.0
    return {"gross_wpm": round(gross, 2), "net_wpm": round(net, 2), "accuracy": round(accuracy, 2)}


def score_text(target: str, typed: str, seconds: float) -> dict:
    matches, errors, error_map = compare_text(target, typed)
    score = calculate_score(len(typed), matches, errors, seconds)
    return {**score, "typed_characters": len(typed), "correct_characters": matches,
            "errors": errors, "error_map": error_map, "completed": typed == target}

