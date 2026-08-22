from __future__ import annotations

from collections import Counter
from math import ceil

DOUBLE_QUOTES = frozenset({'"', '“', '”', '„', '‟'})
SINGLE_QUOTES = frozenset({"'", '‘', '’', '‚', '‛'})
MULTIPLICATION_MARKS = frozenset({'*', '×'})


def _is_multiplication_x(target: str, index: int) -> bool:
    """Recognize x as an operator without treating x inside a word as a symbol."""
    if target[index] not in {'x', 'X'}:
        return False
    left = index - 1
    while left >= 0 and target[left].isspace():
        left -= 1
    right = index + 1
    while right < len(target) and target[right].isspace():
        right += 1
    if left < 0 or right >= len(target):
        return False
    separated = (index > 0 and target[index - 1].isspace()
                 and index + 1 < len(target) and target[index + 1].isspace())
    numeric = target[left].isdigit() or target[right].isdigit()
    grouped = target[left] in ')]}' or target[right] in '([{'
    left_start = left
    while left_start >= 0 and target[left_start].isalnum():
        left_start -= 1
    right_end = right
    while right_end < len(target) and target[right_end].isalnum():
        right_end += 1
    symbolic = (separated and left - left_start == 1 and right_end - right == 1
                and target[left].isalnum() and target[right].isalnum())
    return numeric or grouped or symbolic


def characters_equivalent(expected: str, typed: str, target: str, index: int) -> bool:
    """Return whether a typed character is an accepted form of the target key."""
    if expected == typed:
        return True
    if expected in DOUBLE_QUOTES and typed in DOUBLE_QUOTES:
        return True
    if expected in SINGLE_QUOTES and typed in SINGLE_QUOTES:
        return True
    if expected in MULTIPLICATION_MARKS and typed in MULTIPLICATION_MARKS | {'x', 'X'}:
        return True
    return (_is_multiplication_x(target, index)
            and typed in MULTIPLICATION_MARKS | {'x', 'X'})


def align_text(target: str, typed: str) -> list[dict[str, str]]:
    """Return a minimum-edit alignment with adjacent transpositions.

    Operations consume characters from target, typed, or both. Stable tie
    priorities favor matches and substitutions, producing useful educational
    feedback even when a passage contains repeated letters or spaces.
    """
    rows, columns = len(target) + 1, len(typed) + 1
    cost = [[0] * columns for _ in range(rows)]
    back: list[list[tuple[str, int, int] | None]] = [[None] * columns for _ in range(rows)]
    for i in range(1, rows):
        cost[i][0] = i
        back[i][0] = ("delete", i - 1, 0)
    for j in range(1, columns):
        cost[0][j] = j
        back[0][j] = ("insert", 0, j - 1)

    for i in range(1, rows):
        for j in range(1, columns):
            same = characters_equivalent(target[i - 1], typed[j - 1], target, i - 1)
            candidates = [
                (cost[i - 1][j - 1] + (0 if same else 1), 0 if same else 2,
                 "match" if same else "substitute", i - 1, j - 1),
                (cost[i - 1][j] + 1, 3, "delete", i - 1, j),
                (cost[i][j - 1] + 1, 4, "insert", i, j - 1),
            ]
            if (i >= 2 and j >= 2
                    and characters_equivalent(target[i - 2], typed[j - 1], target, i - 2)
                    and characters_equivalent(target[i - 1], typed[j - 2], target, i - 1)):
                candidates.append((cost[i - 2][j - 2] + 1, 1, "transpose", i - 2, j - 2))
            best = min(candidates, key=lambda item: (item[0], item[1]))
            cost[i][j] = best[0]
            back[i][j] = (best[2], best[3], best[4])

    operations: list[dict[str, str]] = []
    i, j = len(target), len(typed)
    while i or j:
        operation, previous_i, previous_j = back[i][j]  # type: ignore[misc]
        operations.append({
            "op": operation,
            "expected": target[previous_i:i],
            "typed": typed[previous_j:j],
        })
        i, j = previous_i, previous_j
    operations.reverse()
    return operations


def alignment_summary(target: str, typed: str) -> dict:
    operations = align_text(target, typed)
    counts = Counter(operation["op"] for operation in operations)
    error_map: Counter[str] = Counter()
    for operation in operations:
        if operation["op"] in {"substitute", "delete", "transpose"}:
            for expected in operation["expected"]:
                error_map[expected if expected != " " else "space"] += 1
        elif operation["op"] == "insert":
            for extra in operation["typed"]:
                label = "space" if extra == " " else extra
                error_map[f"extra {label}"] += 1
    return {
        "operations": operations,
        "matches": counts["match"],
        "substitutions": counts["substitute"],
        "insertions": counts["insert"],
        "deletions": counts["delete"],
        "transpositions": counts["transpose"],
        "error_map": dict(error_map),
        "key_stats": key_statistics(target, operations),
    }


def _key_label(character: str) -> str:
    return "space" if character == " " else character.lower()


def key_statistics(target: str, operations: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    """Return server-authoritative opportunities, matches, and errors per key."""
    statistics: dict[str, dict[str, int]] = {}
    for character in target:
        label = _key_label(character)
        statistics.setdefault(label, {"expected": 0, "matched": 0, "errors": 0})["expected"] += 1
    for operation in operations:
        if operation["op"] == "match":
            label = _key_label(operation["expected"])
            statistics[label]["matched"] += 1
        elif operation["op"] in {"substitute", "delete", "transpose"}:
            for character in operation["expected"]:
                statistics[_key_label(character)]["errors"] += 1
        elif operation["op"] == "insert":
            for character in operation["typed"]:
                label = f"extra {_key_label(character)}"
                statistics.setdefault(label, {"expected": 0, "matched": 0, "errors": 0})["errors"] += 1
    return statistics


def completion_threshold(target_length: int) -> int:
    return max(1, ceil(target_length * 0.85))


def calculate_score(typed_characters: int, correct_characters: int, errors: int, seconds: float) -> dict[str, float]:
    """Compatibility helper used by historical callers and formula tests."""
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
    if seconds <= 0:
        raise ValueError("Duration must be positive.")
    alignment = alignment_summary(target, typed)
    matches = alignment["matches"]
    error_units = sum(alignment[name] for name in ("substitutions", "insertions", "deletions", "transpositions"))
    denominator = matches + error_units
    minutes = seconds / 60
    gross_wpm = len(typed) / 5 / minutes
    adjusted_wpm = matches / 5 / minutes
    accuracy = matches / denominator * 100 if denominator else 0.0
    return {
        "gross_wpm": round(gross_wpm, 2),
        "adjusted_wpm": round(adjusted_wpm, 2),
        "net_wpm": round(adjusted_wpm, 2),  # Existing reports retain their column.
        "accuracy": round(accuracy, 2),
        "typed_characters": len(typed),
        "correct_characters": matches,
        "errors": error_units,
        "completed": len(typed) >= completion_threshold(len(target)),
        **alignment,
    }
