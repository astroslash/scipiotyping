from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import click
from flask import current_app

REQUIRED = {"id", "title", "text", "category", "difficulty", "age", "objectives", "source", "rights"}
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]+$")


def validate_passages(passages: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(passages, list):
        return ["Content root must be a list."]
    seen: set[str] = set()
    for index, passage in enumerate(passages):
        label = f"Passage {index + 1}"
        if not isinstance(passage, dict):
            errors.append(f"{label} must be an object.")
            continue
        missing = REQUIRED - passage.keys()
        if missing:
            errors.append(f"{label} is missing: {', '.join(sorted(missing))}.")
        pid = passage.get("id", "")
        if not isinstance(pid, str) or not ID_PATTERN.fullmatch(pid):
            errors.append(f"{label} has an invalid id.")
        if pid in seen:
            errors.append(f"Duplicate id: {pid}.")
        seen.add(pid)
        if not isinstance(passage.get("text"), str) or len(passage.get("text", "")) < 80:
            errors.append(f"{label} text must contain at least 80 characters.")
        for field in ("title", "category", "source"):
            if not isinstance(passage.get(field), str) or not passage.get(field, "").strip():
                errors.append(f"{label} {field} must not be blank.")
        if not isinstance(passage.get("age"), int) or not 6 <= passage.get("age", 0) <= 18:
            errors.append(f"{label} age must be 6 through 18.")
        if not isinstance(passage.get("objectives"), list):
            errors.append(f"{label} objectives must be a list.")
        if passage.get("difficulty") not in range(1, 6):
            errors.append(f"{label} difficulty must be 1 through 5.")
        if passage.get("rights") not in {"original", "public-domain", "adapted-public-domain"}:
            errors.append(f"{label} has unsupported rights metadata.")
    return errors


def estimate_difficulty(text: str) -> int:
    words = text.split()
    average = sum(len(word.strip(".,;:!?\"'()")) for word in words) / max(1, len(words))
    punctuation = sum(text.count(mark) for mark in ";:—()")
    score = 1 + (len(words) >= 45) + (average >= 5.2) + (punctuation >= 2) + (len(words) >= 80)
    return min(5, score)


@lru_cache(maxsize=4)
def load_passages(path_string: str) -> list[dict]:
    path = Path(path_string)
    passages = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_passages(passages)
    if errors:
        raise ValueError("\n".join(errors))
    for passage in passages:
        passage["word_count"] = len(passage["text"].split())
        passage["character_count"] = len(passage["text"])
        passage["estimated_difficulty"] = estimate_difficulty(passage["text"])
    return passages


@click.command("validate-content")
def validate_content_command() -> None:
    path = Path(current_app.config["CONTENT_PATH"])
    raw = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_passages(raw)
    if errors:
        raise click.ClickException("\n".join(errors))
    click.echo(f"Validated {len(raw)} passages with no errors.")
