import json
import re

import pytest
from flask import Flask

from scipiotyping import _prepare_instance_path, _validate_hosted_config, create_app
from scipiotyping.db import HybridRow, PostgresConnection, _hybrid_row_factory, get_db


def hosted_app(tmp_path):
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "hosted-test-secret-key-at-least-32-characters",
        "DATABASE": str(tmp_path / "hosted-test.db"),
        "DATABASE_URL": "",
        "HOSTED_MODE": True,
        "PARENT_PASSWORD": "parent-password",
        "SEED_PROFILE_PINS": {"Kenneth": "1111", "William": "2222", "Alice": "3333"},
    })


def csrf_from(response):
    return re.search(rb'name="csrf-token" content="([^"]+)"', response.data).group(1).decode()


def post(client, path, csrf, data=None, **kwargs):
    return client.post(path, data={"csrf_token": csrf, **(data or {})}, **kwargs)


def test_hosted_learner_access(tmp_path):
    app = hosted_app(tmp_path)
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert "FAMILY_PASSWORD" not in app.config
    client = app.test_client()
    assert client.get("/health").status_code == 200
    profiles = client.get("/", follow_redirects=True)
    assert profiles.request.path == "/profiles"
    assert b"Welcome to ScipioTyping" in profiles.data
    assert b"Kenneth" in profiles.data and b"William" in profiles.data and b"Alice" in profiles.data
    csrf = csrf_from(profiles)
    assert client.get("/access").headers["Location"].endswith("/profiles")
    assert client.get("/").headers["Location"].endswith("/profiles")

    wrong_pin = post(client, "/profiles/1/select", csrf, {"pin": "9999"}, follow_redirects=True)
    assert b"did not match" in wrong_pin.data
    home = post(client, "/profiles/1/select", csrf, {"pin": "1111"}, follow_redirects=True)
    assert b"Salve, Kenneth" in home.data
    switch = post(client, "/profiles/2/select", csrf, {"pin": "2222"}, follow_redirects=True)
    assert b"Salve, William" in switch.data


def test_hosted_parent_password_and_json_backup(tmp_path):
    app = hosted_app(tmp_path)
    client = app.test_client()
    csrf = csrf_from(client.get("/profiles"))
    post(client, "/profiles/3/select", csrf, {"pin": "3333"})
    locked = client.get("/parent")
    assert b"Parent area locked" in locked.data and b"Parent password" in locked.data
    wrong = post(client, "/parent/unlock", csrf, {"password": "wrong"}, follow_redirects=True)
    assert b"did not match" in wrong.data
    dashboard = post(client, "/parent/unlock", csrf, {"password": "parent-password"}, follow_redirects=True)
    assert b"Parent dashboard" in dashboard.data and b"private hosted database" in dashboard.data
    backup = client.get("/parent/backup")
    payload = json.loads(backup.data)
    assert payload["format"] == "scipiotyping-cloud-backup"
    assert [profile["name"] for profile in payload["tables"]["profiles"]] == ["Kenneth", "William", "Alice"]
    assert all("pin_hash" not in profile for profile in payload["tables"]["profiles"])


def test_hosted_profile_creation_requires_pin(tmp_path):
    app = hosted_app(tmp_path)
    client = app.test_client()
    csrf = csrf_from(client.get("/profiles"))
    post(client, "/profiles/1/select", csrf, {"pin": "1111"})
    post(client, "/parent/unlock", csrf, {"password": "parent-password"})
    response = post(client, "/parent/profiles", csrf, {"name": "No Pin"}, follow_redirects=True)
    assert b"must contain" in response.data
    post(client, "/parent/profiles", csrf, {"name": "Cousin", "pin": "4444"})
    with app.app_context():
        assert get_db().execute("SELECT pin_hash FROM profiles WHERE name='Cousin'").fetchone()[0]


def test_postgres_compatibility_helpers():
    row = HybridRow(("id", "name"), (7, "Kenneth"))
    assert row[0] == row["id"] == 7 and dict(row)["name"] == "Kenneth"
    assert PostgresConnection._sql("SELECT * FROM profiles WHERE id=?") == \
        "SELECT * FROM profiles WHERE id=%s"

    class CommandCursor:
        description = None

    # PostgreSQL DDL such as CREATE TABLE has no result columns. Startup must
    # still be able to construct the cursor without crashing the row factory.
    assert dict(_hybrid_row_factory(CommandCursor())(())) == {}


def test_hosted_startup_rejects_missing_or_weak_secrets():
    app = Flask(__name__)
    app.config.update(
        HOSTED_MODE=True,
        TESTING=False,
        DATABASE_URL="postgresql://example.invalid/database",
        SECRET_KEY="short",
        PARENT_PASSWORD="parent-password",
        SEED_PROFILE_PINS={"Kenneth": "1111", "William": "2222", "Alice": "3333"},
    )
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        _validate_hosted_config(app)
    app.config["SECRET_KEY"] = "a" * 32
    app.config["PARENT_PASSWORD"] = "short"
    with pytest.raises(RuntimeError, match="PARENT_PASSWORD"):
        _validate_hosted_config(app)
    app.config["PARENT_PASSWORD"] = "different-parent-password"
    app.config["SEED_PROFILE_PINS"]["Alice"] = "2222"
    with pytest.raises(RuntimeError, match="distinct"):
        _validate_hosted_config(app)


def test_hosted_startup_does_not_create_local_instance_directory(tmp_path):
    instance = tmp_path / "read-only-deployment" / "instance"
    _prepare_instance_path(str(instance), hosted=True)
    assert not instance.exists()
    _prepare_instance_path(str(instance), hosted=False)
    assert instance.is_dir()
