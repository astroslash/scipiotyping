import io
import json
import re

from scipiotyping.db import get_db


def post_form(client, path, csrf, data=None, **kwargs):
    return client.post(path, data={"csrf_token":csrf, **(data or {})}, **kwargs)


def test_health_and_primary_pages(client):
    assert client.get("/health").get_json()["schema"] == 4
    for path in ["/", "/library", "/lessons", "/placement", "/progress", "/profiles", "/parent", "/help", "/practice/marathon-messenger"]:
        assert client.get(path).status_code == 200


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


def test_attempt_rejects_client_metrics_and_bad_text(client, csrf):
    response=client.post("/api/attempts",headers={"X-CSRF-Token":csrf},json={"passage_id":"marathon-messenger","duration_seconds":0,"typed_text":"x","accuracy":1000})
    assert response.status_code==400


def test_profile_create_and_select(client, csrf, app):
    response=post_form(client,"/parent/profiles",csrf,{"name":"Alex"})
    assert response.status_code==302
    with app.app_context(): profile=get_db().execute("SELECT * FROM profiles WHERE name='Alex'").fetchone()
    assert post_form(client,f"/profiles/{profile['id']}/select",csrf).status_code==302
    assert b"Salve, Alex" in client.get("/").data


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
