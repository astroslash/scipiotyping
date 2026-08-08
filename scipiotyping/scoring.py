from __future__ import annotations


def calculate_score(typed_characters: int, correct_characters: int, errors: int, seconds: float) -> dict:
    if seconds <= 0:
        raise ValueError("Duration must be positive.")
    typed_characters = max(0, int(typed_characters))
    correct_characters = max(0, min(int(correct_characters), typed_characters))
    errors = max(0, int(errors))
    minutes = seconds / 60
    gross = typed_characters / 5 / minutes
    net = max(0.0, gross - errors / minutes)
    accuracy = (correct_characters / typed_characters * 100) if typed_characters else 0.0
    return {"gross_wpm": round(gross, 2), "net_wpm": round(net, 2), "accuracy": round(accuracy, 2)}

