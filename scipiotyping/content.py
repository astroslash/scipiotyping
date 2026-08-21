from __future__ import annotations

import json
import math
import re
from collections import Counter
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

import click
from flask import current_app

BASE_REQUIRED = {
    "id", "title", "text", "category", "difficulty", "age", "objectives",
    "context", "vocabulary", "source", "rights",
}
BUILTIN_REQUIRED = BASE_REQUIRED | {
    "typing_focus", "reading_level", "revision", "added_in",
    "review_status", "reviewed_on", "references",
}
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]+$")
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RIGHTS = {"original", "public-domain", "adapted-public-domain"}
SCHOOL_LEVELS = {"elementary", "middle"}


def _nonblank_strings(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def validate_passages(passages: object, *, strict: bool = False) -> list[str]:
    """Validate custom-compatible passages, with stricter built-in checks on request."""
    errors: list[str] = []
    if not isinstance(passages, list):
        return ["Content root must be a list."]
    seen_ids: set[str] = set()
    seen_titles: set[str] = set()
    seen_texts: set[str] = set()
    required = BUILTIN_REQUIRED if strict else BASE_REQUIRED
    for index, passage in enumerate(passages):
        label = f"Passage {index + 1}"
        if not isinstance(passage, dict):
            errors.append(f"{label} must be an object.")
            continue
        pid = passage.get("id", "")
        if isinstance(pid, str) and pid:
            label = f"Passage '{pid}'"
        missing = required - passage.keys()
        if missing:
            errors.append(f"{label} is missing: {', '.join(sorted(missing))}.")
        if not isinstance(pid, str) or not ID_PATTERN.fullmatch(pid):
            errors.append(f"{label} has an invalid id.")
        if pid in seen_ids:
            errors.append(f"Duplicate id: {pid}.")
        seen_ids.add(pid)

        text = passage.get("text", "")
        if not isinstance(text, str) or len(text) < 80:
            errors.append(f"{label} text must contain at least 80 characters.")
        elif strict and not 35 <= len(text.split()) <= 220:
            errors.append(f"{label} must contain 35 through 220 words.")
        normalized_text = " ".join(text.casefold().split()) if isinstance(text, str) else ""
        if normalized_text and normalized_text in seen_texts:
            errors.append(f"Duplicate text in {label}.")
        seen_texts.add(normalized_text)

        for field in ("title", "category", "context", "source"):
            if not isinstance(passage.get(field), str) or not passage.get(field, "").strip():
                errors.append(f"{label} {field} must not be blank.")
        title_key = passage.get("title", "").strip().casefold() if isinstance(passage.get("title"), str) else ""
        if title_key and title_key in seen_titles:
            errors.append(f"Duplicate title: {passage.get('title')}.")
        seen_titles.add(title_key)
        if not isinstance(passage.get("age"), int) or not 6 <= passage.get("age", 0) <= 18:
            errors.append(f"{label} age must be 6 through 18.")
        if passage.get("difficulty") not in range(1, 6):
            errors.append(f"{label} difficulty must be 1 through 5.")
        if not _nonblank_strings(passage.get("objectives")):
            errors.append(f"{label} objectives must be a list of nonblank strings.")
        if not _nonblank_strings(passage.get("vocabulary")) and passage.get("vocabulary") != []:
            errors.append(f"{label} vocabulary must be a list of nonblank strings.")
        if passage.get("rights") not in RIGHTS:
            errors.append(f"{label} has unsupported rights metadata.")
        if passage.get("school_level", "middle") not in SCHOOL_LEVELS:
            errors.append(f"{label} school_level must be elementary or middle.")

        if strict:
            if not _nonblank_strings(passage.get("typing_focus")):
                errors.append(f"{label} typing_focus must be a list of nonblank strings.")
            if not isinstance(passage.get("reading_level"), int) or not 3 <= passage.get("reading_level", 0) <= 10:
                errors.append(f"{label} reading_level must be grade 3 through 10.")
            if not isinstance(passage.get("revision"), int) or passage.get("revision", 0) < 1:
                errors.append(f"{label} revision must be a positive integer.")
            if not isinstance(passage.get("added_in"), str) or not VERSION_PATTERN.fullmatch(passage.get("added_in", "")):
                errors.append(f"{label} added_in must be a semantic version.")
            if passage.get("review_status") != "reviewed":
                errors.append(f"{label} must be reviewed before release.")
            if not isinstance(passage.get("reviewed_on"), str) or not DATE_PATTERN.fullmatch(passage.get("reviewed_on", "")):
                errors.append(f"{label} reviewed_on must use YYYY-MM-DD.")
            references = passage.get("references")
            if not isinstance(references, list) or not references:
                errors.append(f"{label} references must be a nonempty list.")
            elif any(not isinstance(reference, dict) or not isinstance(reference.get("citation"), str)
                     or not reference["citation"].strip() for reference in references):
                errors.append(f"{label} references must contain nonblank citation objects.")
    return errors


def estimate_difficulty(text: str) -> int:
    words = text.split()
    average = sum(len(word.strip(".,;:!?\"'()")) for word in words) / max(1, len(words))
    punctuation = sum(text.count(mark) for mark in ";:\u2014()")
    score = 1 + (len(words) >= 45) + (average >= 5.2) + (punctuation >= 2) + (len(words) >= 80)
    return min(5, score)


def enrich_passage(passage: dict, *, custom: bool = False) -> dict:
    item = dict(passage)
    item.setdefault("typing_focus", item.get("objectives", ["accuracy"]))
    item.setdefault("reading_level", max(3, min(10, int(item.get("age", 10)) - 5)))
    item.setdefault("school_level", "elementary" if item["reading_level"] == 3 else "middle")
    item.setdefault("revision", 1)
    item.setdefault("added_in", "custom" if custom else "1.0.0")
    item.setdefault("review_status", "household" if custom else "reviewed")
    item["word_count"] = len(item["text"].split())
    item["character_count"] = len(item["text"])
    item["estimated_difficulty"] = estimate_difficulty(item["text"])
    item["estimated_minutes"] = max(1, math.ceil(item["word_count"] / 25))
    item["is_custom"] = custom
    return item


def _read_content(path: Path) -> tuple[list[dict], int, list[str]]:
    if path.is_file():
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw, 1, [path.name]
    manifest_path = path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 2 or not _nonblank_strings(manifest.get("files")):
        raise ValueError("content/manifest.json must declare schema_version 2 and a nonempty files list.")
    if len(manifest["files"]) != len(set(manifest["files"])):
        raise ValueError("content/manifest.json contains a duplicate filename.")
    passages: list[dict] = []
    filenames: list[str] = []
    root = path.resolve()
    for relative in manifest["files"]:
        source = (path / relative).resolve()
        if root not in source.parents or source.suffix.lower() != ".json":
            raise ValueError(f"Unsafe content filename in manifest: {relative}.")
        raw = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError(f"{relative} must contain a JSON list.")
        passages.extend(raw)
        filenames.append(relative)
    legacy_ids = manifest.get("legacy_ids", [])
    if not _nonblank_strings(legacy_ids) or len(legacy_ids) != len(set(legacy_ids)):
        raise ValueError("content/manifest.json must contain unique legacy_ids.")
    current_ids = {item.get("id") for item in passages if isinstance(item, dict)}
    missing_legacy = sorted(set(legacy_ids) - current_ids)
    if missing_legacy:
        raise ValueError(f"Legacy passage IDs may not be removed: {', '.join(missing_legacy)}.")
    return passages, 2, filenames


@lru_cache(maxsize=8)
def load_passages(path_string: str) -> list[dict]:
    path = Path(path_string)
    passages, schema_version, _files = _read_content(path)
    errors = validate_passages(passages, strict=schema_version >= 2)
    if errors:
        raise ValueError("\n".join(errors))
    return [enrich_passage(passage) for passage in passages if passage.get("review_status", "reviewed") == "reviewed"]


def similar_passage_warnings(passages: list[dict], threshold: float = 0.92) -> list[str]:
    warnings: list[str] = []
    normalized = [(item["id"], " ".join(item["text"].casefold().split())) for item in passages]
    for index, (left_id, left_text) in enumerate(normalized):
        for right_id, right_text in normalized[index + 1:]:
            if SequenceMatcher(None, left_text, right_text).ratio() >= threshold:
                warnings.append(f"Possible near-duplicate: {left_id} and {right_id}.")
    return warnings


def content_report(passages: list[dict]) -> dict:
    return {
        "total": len(passages),
        "categories": dict(sorted(Counter(item["category"] for item in passages).items())),
        "difficulties": dict(sorted(Counter(item["difficulty"] for item in passages).items())),
        "reading_levels": dict(sorted(Counter(item["reading_level"] for item in passages).items())),
        "school_levels": dict(sorted(Counter(item["school_level"] for item in passages).items())),
        "rights": dict(sorted(Counter(item["rights"] for item in passages).items())),
        "review_status": dict(sorted(Counter(item["review_status"] for item in passages).items())),
        "word_count": {
            "minimum": min((item["word_count"] for item in passages), default=0),
            "maximum": max((item["word_count"] for item in passages), default=0),
            "average": round(sum(item["word_count"] for item in passages) / max(1, len(passages)), 1),
        },
        "similarity_warnings": similar_passage_warnings(passages),
    }


def render_inventory(passages: list[dict]) -> str:
    report = content_report(passages)
    category_rows = "\n".join(f"| {name} | {count} |" for name, count in report["categories"].items())
    difficulty_rows = "\n".join(f"| Level {level} | {count} |" for level, count in report["difficulties"].items())
    school_rows = "\n".join(
        f"| {'Elementary' if level == 'elementary' else 'Middle School'} | {count} |"
        for level, count in report["school_levels"].items()
    )
    return f"""# Content inventory

This file is generated by `flask content-report --write-inventory`.

The ScipioTyping library contains {report['total']} reviewed built-in passages. The application also
supplies fourteen original focused typing drills. Custom household passages are stored in SQLite
and are not included in this inventory.

## Subjects

| Category | Count |
|---|---:|
{category_rows}

## School level

| Audience | Count |
|---|---:|
{school_rows}

## Typing difficulty

| Difficulty | Count |
|---|---:|
{difficulty_rows}

Word counts range from {report['word_count']['minimum']} to {report['word_count']['maximum']},
with an average of {report['word_count']['average']} words. All built-in passages have reviewed
source, rights, reading-level, revision, and typing-focus metadata.
"""


@click.command("validate-content")
def validate_content_command() -> None:
    path = Path(current_app.config["CONTENT_PATH"])
    try:
        passages, schema_version, files = _read_content(path)
        errors = validate_passages(passages, strict=schema_version >= 2)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise click.ClickException(str(error)) from error
    if errors:
        raise click.ClickException("\n".join(errors))
    warnings = similar_passage_warnings(passages)
    click.echo(f"Validated {len(passages)} passages in {len(files)} file(s) with no errors.")
    for warning in warnings:
        click.echo(f"Warning: {warning}")


@click.command("content-report")
@click.option("--write-inventory", is_flag=True, help="Update docs/content-inventory.md.")
def content_report_command(write_inventory: bool) -> None:
    items = load_passages(current_app.config["CONTENT_PATH"])
    report = content_report(items)
    click.echo(json.dumps(report, indent=2))
    if write_inventory:
        destination = Path(current_app.root_path).parent / "docs" / "content-inventory.md"
        destination.write_text(render_inventory(items), encoding="utf-8")
        click.echo(f"Updated {destination}.")
