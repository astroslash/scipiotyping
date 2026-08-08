"""ScipioTyping application factory."""
from __future__ import annotations

import os
import secrets
from pathlib import Path

from flask import Flask

from . import db
from .content import load_passages, validate_content_command
from .lessons import lesson_passages
from .routes import bp
from .security import csrf_token, protect_csrf

__version__ = "1.2.0"


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    secret_file = Path(app.instance_path) / ".secret_key"
    if not os.environ.get("SECRET_KEY") and not test_config:
        if not secret_file.exists():
            secret_file.write_text(secrets.token_hex(32), encoding="ascii")
        local_secret = secret_file.read_text(encoding="ascii").strip()
    else:
        local_secret = os.environ.get("SECRET_KEY", "testing-only")
    app.config.from_mapping(
        SECRET_KEY=local_secret,
        DATABASE=os.environ.get("SCIPIO_DATABASE", str(Path(app.instance_path) / "scipiotyping.db")),
        CONTENT_PATH=str(Path(app.root_path).parent / "content" / "passages.json"),
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    db.init_app(app)
    app.cli.add_command(validate_content_command)
    app.register_blueprint(bp)
    app.before_request(protect_csrf)
    app.jinja_env.globals["csrf_token"] = csrf_token
    with app.app_context():
        db.init_database()
        lookup = {item["id"]: item["text"] for item in load_passages(app.config["CONTENT_PATH"])}
        lookup.update({item["id"]: item["text"] for item in lesson_passages()})
        lookup.update({row["id"]: row["text"] for row in db.get_db().execute("SELECT id,text FROM custom_passages")})
        db.backfill_key_stats(db.get_db(), lookup)
        db.backfill_practice_sessions(db.get_db())
    return app
