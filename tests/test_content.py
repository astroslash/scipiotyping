import json

from scipiotyping.content import load_passages, validate_passages


def test_builtin_library_has_sixty_balanced_passages(app):
    items = load_passages(app.config["CONTENT_PATH"])
    counts = {}
    for item in items: counts[item["category"]] = counts.get(item["category"], 0) + 1
    assert len(items) == 60 and len(counts) == 10 and set(counts.values()) == {6}


def test_all_content_has_context_and_vocabulary(app):
    for item in load_passages(app.config["CONTENT_PATH"]):
        assert item["context"] and isinstance(item["vocabulary"], list) and item["source"]


def test_duplicate_and_short_content_rejected():
    item = {"id":"same-id","title":"T","text":"short","category":"Test","difficulty":1,"age":10,"objectives":[],"source":"Original","rights":"original"}
    errors = validate_passages([item, dict(item)])
    assert any("Duplicate" in error for error in errors)
    assert any("80" in error for error in errors)


def test_bad_rights_rejected():
    item={"id":"valid-id","title":"Title","text":"x"*100,"category":"Test","difficulty":1,"age":10,"objectives":[],"source":"Unknown","rights":"copyrighted"}
    assert any("rights" in error for error in validate_passages([item]))

