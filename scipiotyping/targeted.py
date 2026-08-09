from __future__ import annotations

import hashlib
import random
import re
from datetime import date

GENERATOR_VERSION = 1


def display_key(key: str) -> str:
    return "Space" if key == "space" else key.upper() if len(key) == 1 else key


def _character(key: str) -> str:
    return " " if key == "space" else key


def targeted_passage(profile_id: int, focus_keys: list[str], source_texts: list[str], day: date | None = None) -> dict:
    """Build a deterministic, local drill emphasizing up to three keys."""
    keys = sorted(dict.fromkeys(focus_keys))[:3] or ["a", "s"]
    stamp = (day or date.today()).isoformat()
    seed_text = f"{profile_id}|{stamp}|{'|'.join(keys)}|{GENERATOR_VERSION}"
    seed = int.from_bytes(hashlib.sha256(seed_text.encode()).digest()[:8], "big")
    randomizer = random.Random(seed)
    fragments: list[str] = []
    for text in source_texts:
        fragments.extend(part.strip() for part in re.split(r"(?<=[.!?;])\s+", text) if len(part.strip()) >= 28)
    characters = [_character(key) for key in keys]
    useful = [fragment for fragment in fragments if any(character.lower() in fragment.lower() for character in characters)]
    randomizer.shuffle(useful)
    useful.sort(key=lambda fragment: sum(fragment.lower().count(character.lower()) for character in characters), reverse=True)
    chosen: list[str] = []
    totals = {key: 0 for key in keys}
    for fragment in useful:
        if len(" ".join(chosen + [fragment])) > 360:
            continue
        helps = any(totals[key] < 10 and fragment.lower().count(_character(key).lower()) for key in keys)
        if helps or len(chosen) < 2:
            chosen.append(fragment)
            for key in keys:
                totals[key] += fragment.lower().count(_character(key).lower())
        if len(" ".join(chosen)) >= 180 and all(total >= 8 for total in totals.values()):
            break
    if not chosen:
        labels = ", ".join(display_key(key) for key in keys)
        chosen = [f"Practice {labels} with calm hands. Accuracy grows when each careful key returns to its proper place."]
    text = " ".join(chosen)
    identifier = hashlib.sha256(seed_text.encode()).hexdigest()[:12]
    return {
        "id": f"targeted-{identifier}",
        "title": "Weak-Key Workshop",
        "text": text,
        "category": "Targeted Practice",
        "difficulty": 1,
        "age": 8,
        "objectives": [f"Improve {display_key(key)}" for key in keys],
        "typing_focus": [f"Improve {display_key(key)}" for key in keys],
        "context": "This private drill was assembled locally from ScipioTyping content using your recent results.",
        "vocabulary": [],
        "source": "Locally generated from ScipioTyping passages",
        "rights": "original",
        "word_count": len(text.split()),
        "character_count": len(text),
        "focus_keys": keys,
        "generator_version": GENERATOR_VERSION,
        "revision": GENERATOR_VERSION,
        "seed": seed_text,
    }
