from __future__ import annotations

LESSONS = [
    {"id":"home-row","title":"Home Row Command","level":1,"focus":"asdf jkl;","description":"Build calm, accurate movement from the home keys."},
    {"id":"upper-row","title":"The Upper Ranks","level":1,"focus":"qwerty uiop","description":"Reach upward and return to home position."},
    {"id":"lower-row","title":"The Lower Ranks","level":2,"focus":"zxcv bnm","description":"Reach downward without collapsing hand position."},
    {"id":"capitals","title":"Names and Capitals","level":2,"focus":"Shift","description":"Use the opposite-hand Shift key for proper names."},
    {"id":"punctuation","title":"Punctuation Signals","level":3,"focus":",.;:'\"?!","description":"Practice stops, pauses, quotations, and questions."},
    {"id":"numbers","title":"Dates and Numbers","level":3,"focus":"0123456789","description":"Type dates and quantities with control."},
    {"id":"symbols","title":"Mathematical Symbols","level":4,"focus":"+-=()%","description":"Practice notation used in mathematical explanations."},
    {"id":"mastery","title":"Scholar's Challenge","level":5,"focus":"all keys","description":"Longer, complex passages for accuracy and speed."},
]

DRILL_TEXTS = {
    "home-row": "ask a lad; a flask; all fall; dad asks; a sad salad; jak falls; a hall; a lad asks; all lads fall; ask dad; a flask; all fall;",
    "upper-row": "write your quiet route; type it true; power your tower; quite a proper report; write it out; try your upper row; keep your route pure;",
    "lower-row": "zoom back; move a calm cabin; mix cocoa; examine a bronze maze; come back; move a box; zinc can mix; brave men can examine maps;",
    "capitals": "Athena guided Odysseus. Rome built roads. Mali traded gold. Euclid studied geometry. Kenneth practices with patience. Persia met Greece.",
    "punctuation": "Ready, steady, type! Who planned the route? Kenneth replied, \"We did.\" Accuracy first; speed follows. Pause, think, and continue.",
    "numbers": "Marathon was fought in 490 BCE. Waterloo came in 1815. A chessboard has 64 squares: 32 light and 32 dark. Practice for 15 minutes.",
    "symbols": "If a + b = 12, then b = 12 - a. A circle uses pi: C = 2 × pi × r. Probability ranges from 0% to 100%. Try (3 + 5) × 2 = 16.",
    "mastery": "A disciplined scholar asks difficult questions, checks the evidence, and revises mistaken conclusions. Speed serves understanding; it cannot replace it.",
}


def unlocked_lessons(level: int) -> list[dict]:
    return [{**lesson, "unlocked": lesson["level"] <= max(1, level)} for lesson in LESSONS]


def lesson_passages() -> list[dict]:
    return [{"id": f"drill-{lesson['id']}", "title": lesson["title"], "text": DRILL_TEXTS[lesson["id"]],
             "category": "Typing Fundamentals", "difficulty": lesson["level"], "age": 8,
             "objectives": [lesson["focus"]], "typing_focus": [lesson["focus"]],
             "context": lesson["description"], "vocabulary": [],
             "source": "Original ScipioTyping drill", "rights": "original",
             "revision": 1, "added_in": "1.0.0", "reading_level": 3,
             "word_count": len(DRILL_TEXTS[lesson["id"]].split()), "character_count": len(DRILL_TEXTS[lesson["id"]])}
            for lesson in LESSONS]


def progression_level(base_level: int, completed_lesson_ids: set[str]) -> int:
    level = max(1, min(5, base_level))
    while level < 5:
        required = {lesson["id"] for lesson in LESSONS if lesson["level"] == level}
        if required and required.issubset(completed_lesson_ids):
            level += 1
        else:
            break
    return level


def placement_level(wpm: float, accuracy: float) -> int:
    if accuracy < 85 or wpm < 10: return 1
    if accuracy < 90 or wpm < 18: return 2
    if accuracy < 94 or wpm < 28: return 3
    if accuracy < 97 or wpm < 40: return 4
    return 5
