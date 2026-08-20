import io
import json
import re

from scipiotyping.db import get_db


def post_form(client, path, csrf, data=None, **kwargs):
    return client.post(path, data={"csrf_token":csrf, **(data or {})}, **kwargs)


def test_health_and_primary_pages(client):
    health = client.get("/health").get_json()
    assert health["schema"] == 8 and health["version"] == "1.5.4"
    for path in ["/", "/library", "/lessons", "/placement", "/progress", "/profiles", "/parent", "/help", "/practice/marathon-messenger"]:
        response = client.get(path)
        assert response.status_code == 200
        assert b'id="daily-goal"' in response.data


def test_practice_page_server_renders_passage_text(client):
    from scipiotyping.lessons import DRILL_TEXTS

    response = client.get("/practice/drill-home-row?mode=lesson&lesson=home-row")
    assert response.status_code == 200
    assert b'id="passage"' in response.data
    assert DRILL_TEXTS["home-row"].encode() in response.data


def test_missing_passage_is_404(client):
    assert client.get("/practice/no-such-passage").status_code == 404


def test_library_filters(client):
    response=client.get("/library?category=Chess&difficulty=3&q=pawns")
    assert b"Pawns Are the Soul" in response.data and b"Hannibal" not in response.data


def test_library_paginates_and_preserves_filters(client):
    response = client.get("/library?sort=title")
    assert b"page 1 of 5" in response.data and b">Next<" in response.data
    assert b"sort=title" in response.data


def test_csrf_blocks_post(client):
    assert client.post("/api/attempts",json={}).status_code == 400


def test_attempt_is_scored_by_server(client, csrf, app):
    with app.app_context():
        from scipiotyping.content import load_passages
        passage=next(p for p in load_passages(app.config["CONTENT_PATH"]) if p["id"]=="marathon-messenger")
    response=client.post("/api/attempts",headers={"X-CSRF-Token":csrf},json={"passage_id":passage["id"],"duration_seconds":120,"typed_text":passage["text"],"corrected_errors":2,"error_map":{"x":2},"mode":"practice"})
    data=response.get_json()
    assert response.status_code==201 and data["accuracy"]==100 and data["completed"] is True
    assert "First Expedition" in data["achievements"]
    assert data["session_seconds"] == 120 and data["daily"]["active_seconds"] == 120
    with app.app_context():
        saved_session = get_db().execute("SELECT * FROM practice_sessions").fetchone()
        assert saved_session["attempt_id"] and saved_session["completed_at"]
        saved_attempt = get_db().execute("SELECT * FROM attempts").fetchone()
        assert saved_attempt["target_text"] == passage["text"] and saved_attempt["passage_revision"] == 1


def test_library_completion_status_is_profile_specific(client, csrf, app):
    with app.app_context():
        from scipiotyping.content import load_passages
        passage = next(p for p in load_passages(app.config["CONTENT_PATH"]) if p["id"] == "marathon-messenger")
    response = client.post("/api/attempts", headers={"X-CSRF-Token": csrf}, json={
        "passage_id": passage["id"], "duration_seconds": 60, "typed_text": passage["text"], "mode": "practice"})
    assert response.status_code == 201
    completed = client.get("/library?status=completed")
    untried = client.get("/library?status=not-practiced&q=marathon")
    assert b"The Plain of Marathon" in completed.data and b"Completed" in completed.data
    assert b"The Plain of Marathon" not in untried.data
    post_form(client, "/parent/profiles", csrf, {"name": "Alex"})
    with app.app_context():
        alex = get_db().execute("SELECT id FROM profiles WHERE name='Alex'").fetchone()[0]
    post_form(client, f"/profiles/{alex}/select", csrf)
    assert b"The Plain of Marathon" not in client.get("/library?status=completed").data


def test_practice_session_heartbeats_are_idempotent_and_profile_owned(client, csrf, app):
    started = client.post("/api/practice-sessions", headers={"X-CSRF-Token": csrf}, json={
        "passage_id": "marathon-messenger", "mode": "practice"})
    assert started.status_code == 201
    session_id = started.get_json()["id"]
    headers = {"X-CSRF-Token": csrf}
    first = client.patch(f"/api/practice-sessions/{session_id}", headers=headers, json={"active_seconds": .1})
    repeated = client.patch(f"/api/practice-sessions/{session_id}", headers=headers, json={"active_seconds": .1})
    assert first.status_code == repeated.status_code == 200
    assert repeated.get_json()["daily"]["active_seconds"] == .1
    assert client.patch(f"/api/practice-sessions/{session_id}", headers=headers, json={"active_seconds": 99}).status_code == 400
    post_form(client, "/parent/profiles", csrf, {"name": "Alex"})
    with app.app_context():
        alex = get_db().execute("SELECT id FROM profiles WHERE name='Alex'").fetchone()[0]
    post_form(client, f"/profiles/{alex}/select", csrf)
    assert client.patch(f"/api/practice-sessions/{session_id}", headers=headers, json={"active_seconds": .2}).status_code == 400
    assert b'data-base-seconds="0.0"' in client.get("/").data


def test_attempt_with_substitution_completes_and_is_adjusted(client, csrf, app):
    with app.app_context():
        from scipiotyping.content import load_passages
        passage=next(p for p in load_passages(app.config["CONTENT_PATH"]) if p["id"]=="marathon-messenger")
    typed="X" + passage["text"][1:]
    response=client.post("/api/attempts",headers={"X-CSRF-Token":csrf},json={"passage_id":passage["id"],"duration_seconds":120,"typed_text":typed,"corrected_errors":0,"mode":"practice"})
    data=response.get_json()
    assert response.status_code==201 and data["completed"] is True
    assert data["substitutions"]==1 and data["accuracy"]<100
    assert data["adjusted_wpm"]<data["gross_wpm"]
    assert data["key_stats"][passage["text"][0].lower()]["errors"] == 1


def test_targeted_practice_uses_weak_keys_and_stores_reproducible_target(client, csrf, app):
    with app.app_context():
        from scipiotyping.content import load_passages
        passage = next(p for p in load_passages(app.config["CONTENT_PATH"]) if p["id"] == "marathon-messenger")
    typed = "".join("x" if character.lower() == "a" else character for character in passage["text"])
    response = client.post("/api/attempts", headers={"X-CSRF-Token": csrf}, json={
        "passage_id": passage["id"], "duration_seconds": 120, "typed_text": typed, "mode": "practice"})
    assert response.status_code == 201
    progress = client.get("/progress")
    assert b"Keyboard progress" in progress.data and b"Practice weak keys" in progress.data
    assert b'aria-label="Per-key recent accuracy"' in progress.data
    assert b"Needs practice" in progress.data and b"Not enough data" in progress.data
    workshop = client.get("/practice/targeted")
    assert workshop.status_code == 200 and b"Weak-Key Workshop" in workshop.data
    with client.session_transaction() as state:
        target = state["targeted_passage"]
    response = client.post("/api/attempts", headers={"X-CSRF-Token": csrf}, json={
        "passage_id": target["id"], "duration_seconds": 60, "typed_text": target["text"], "mode": "targeted"})
    data = response.get_json()
    assert response.status_code == 201 and data["focus_feedback"]
    assert data["focus_feedback"][0]["baseline_accuracy"] is not None
    assert data["focus_feedback"][0]["recent_accuracy"] is not None
    assert data["focus_feedback"][0]["change"] is not None
    assert "Focused Practice" in data["achievements"]
    with app.app_context():
        row = get_db().execute("SELECT * FROM attempts WHERE mode='targeted'").fetchone()
        assert row["target_text"] == target["text"]
        assert json.loads(row["focus_keys"])
        assert row["generator_version"] == 1


def test_attempt_rejects_client_metrics_and_bad_text(client, csrf):
    response=client.post("/api/attempts",headers={"X-CSRF-Token":csrf},json={"passage_id":"marathon-messenger","duration_seconds":0,"typed_text":"x","accuracy":1000})
    assert response.status_code==400


def test_profile_create_and_select(client, csrf, app):
    response=post_form(client,"/parent/profiles",csrf,{"name":"Alex"})
    assert response.status_code==302
    with app.app_context(): profile=get_db().execute("SELECT * FROM profiles WHERE name='Alex'").fetchone()
    assert post_form(client,f"/profiles/{profile['id']}/select",csrf).status_code==302
    assert b"Salve, Alex" in client.get("/").data


def test_three_family_profiles_are_seeded(app):
    with app.app_context():
        names = [row[0] for row in get_db().execute("SELECT name FROM profiles ORDER BY id")]
    assert names == ["Kenneth", "William", "Alice"]


def test_profile_delete_requires_confirmation(client, csrf, app):
    post_form(client,"/parent/profiles",csrf,{"name":"Temporary"})
    with app.app_context(): profile=get_db().execute("SELECT * FROM profiles WHERE name='Temporary'").fetchone()
    response=post_form(client,f"/parent/profiles/{profile['id']}/delete",csrf,{"confirmation":"DELETE Temporary"},follow_redirects=True)
    assert b"Profile removed" in response.data


def test_parent_settings_validation(client, csrf):
    response=post_form(client,"/parent",csrf,{"daily_goal_minutes":"2","preferred_difficulty":"9"},follow_redirects=True)
    assert b"Use a goal from 5 to 120" in response.data


def test_pin_lock_unlock(client, csrf):
    assert post_form(client,"/parent/pin",csrf,{"pin":"1234"}).status_code==302
    with client.session_transaction() as session: session.pop("parent_unlocked",None)
    assert b"Parent area locked" in client.get("/parent").data
    assert post_form(client,"/parent/unlock",csrf,{"pin":"9999"},follow_redirects=True).status_code==200
    assert post_form(client,"/parent/unlock",csrf,{"pin":"1234"},follow_redirects=True).status_code==200
    assert b"Parent dashboard" in client.get("/parent").data


def test_custom_content_validation_and_add(client, csrf):
    data={"id":"kenneth-test","title":"Kenneth Test","text":"This is an original household passage long enough to meet the required minimum length for careful typing practice.","category":"Family","difficulty":"2","age":"10","context":"A test passage.","source":"Household original"}
    response=post_form(client,"/parent/content",csrf,data,follow_redirects=True)
    assert b"Custom passage added" in response.data
    assert b"Kenneth Test" in client.get("/library?q=kenneth").data


def test_exports_and_backup(client, csrf):
    assert client.get("/export/json").status_code==200
    assert client.get("/export/csv").status_code==200
    assert client.get("/export/time-json").status_code==200
    assert client.get("/export/time-csv").status_code==200
    backup=client.get("/parent/backup")
    assert backup.status_code==200 and backup.data[:16]==b"SQLite format 3\x00"


def test_invalid_restore_does_not_replace_database(client, csrf):
    response=client.post("/parent/restore",data={"csrf_token":csrf,"confirmation":"RESTORE","backup":(io.BytesIO(b"not sqlite"),"bad.db")},content_type="multipart/form-data",follow_redirects=True)
    assert b"not a valid ScipioTyping backup" in response.data
    assert client.get("/health").status_code==200


def test_valid_backup_restore_round_trip(client, csrf, app):
    backup=client.get("/parent/backup").data
    post_form(client,"/parent/profiles",csrf,{"name":"After Backup"})
    response=client.post("/parent/restore",data={"csrf_token":csrf,"confirmation":"RESTORE","backup":(io.BytesIO(backup),"good.db")},content_type="multipart/form-data",follow_redirects=True)
    assert b"Backup restored" in response.data
    with app.app_context(): assert get_db().execute("SELECT 1 FROM profiles WHERE name='After Backup'").fetchone() is None


def test_reset_requires_exact_confirmation(client, csrf, app):
    response=post_form(client,"/parent/reset",csrf,{"confirmation":"RESET"},follow_redirects=True)
    assert b"Type RESET Kenneth exactly" in response.data


def test_reset_removes_attempts_and_unfinished_practice_time(client, csrf, app):
    started = client.post("/api/practice-sessions", headers={"X-CSRF-Token": csrf}, json={
        "passage_id": "marathon-messenger", "mode": "practice"})
    identifier = started.get_json()["id"]
    assert client.patch(f"/api/practice-sessions/{identifier}", headers={"X-CSRF-Token": csrf},
                        json={"active_seconds": .1}).status_code == 200
    response = post_form(client, "/parent/reset", csrf, {"confirmation": "RESET Kenneth"}, follow_redirects=True)
    assert b"Progress reset" in response.data
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM practice_sessions").fetchone()[0] == 0
