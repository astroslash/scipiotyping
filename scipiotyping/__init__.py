"""ScipioTyping application factory."""
from __future__ import annotations

import os
import secrets
from pathlib import Path

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

__version__ = "1.8.0"

DEFAULT_EMILY_PIN = "3333"

from . import db
from .content import content_report_command, load_passages, validate_content_command
from .lessons import lesson_passages
from .routes import bp
from .security import csrf_token, protect_csrf, require_hosted_access


def _hosted_secrets() -> tuple[str, dict[str, str]]:
    parent_password = os.environ.get("SCIPIO_PARENT_PASSWORD", "")
    pins = {
        name: os.environ.get(
            f"SCIPIO_{name.upper()}_PIN",
            DEFAULT_EMILY_PIN if name == "Emily" else "",
        )
        for name in db.SEEDED_PROFILES
    }
    return parent_password, pins


def _validate_hosted_config(app: Flask) -> None:
    if not app.config["HOSTED_MODE"] or app.config.get("TESTING"):
        return
    if not app.config["DATABASE_URL"].startswith(("postgres://", "postgresql://")):
        raise RuntimeError("Hosted ScipioTyping requires a PostgreSQL DATABASE_URL.")
    if len(app.config["SECRET_KEY"]) < 32:
        raise RuntimeError("Hosted ScipioTyping requires a SECRET_KEY of at least 32 characters.")
    if len(app.config["PARENT_PASSWORD"]) < 12:
        raise RuntimeError("SCIPIO_PARENT_PASSWORD must contain at least 12 characters.")
    pins = app.config["SEED_PROFILE_PINS"]
    original_pins = [pins[name] for name in db.SEEDED_PROFILES if name != "Emily"]
    if set(pins) != set(db.SEEDED_PROFILES) or any(
        not pin.isdigit() or not 4 <= len(pin) <= 10 for pin in pins.values()
    ) or len(set(original_pins)) != len(original_pins):
        raise RuntimeError("Every saved learner requires a 4–10 digit PIN; Kenneth, William, and Alice must remain distinct.")


def _prepare_instance_path(instance_path: str, hosted: bool) -> None:
    """Create local storage only where the filesystem is persistent and writable."""
    if not hosted:
        Path(instance_path).mkdir(parents=True, exist_ok=True)


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    database_url = os.environ.get("DATABASE_URL", "")
    hosted_environment = bool(database_url or os.environ.get("VERCEL"))
    _prepare_instance_path(app.instance_path, hosted_environment)
    secret_file = Path(app.instance_path) / ".secret_key"
    if not os.environ.get("SECRET_KEY") and not test_config and not hosted_environment:
        if not secret_file.exists():
            secret_file.write_text(secrets.token_hex(32), encoding="ascii")
        local_secret = secret_file.read_text(encoding="ascii").strip()
    else:
        local_secret = os.environ.get("SECRET_KEY", "testing-only")
    parent_password, seed_pins = _hosted_secrets()
    app.config.from_mapping(
        SECRET_KEY=local_secret,
        DATABASE=os.environ.get("SCIPIO_DATABASE", str(Path(app.instance_path) / "scipiotyping.db")),
        DATABASE_URL=database_url,
        HOSTED_MODE=hosted_environment,
        PARENT_PASSWORD=parent_password,
        SEED_PROFILE_PINS={name: pin for name, pin in seed_pins.items() if pin},
        CONTENT_PATH=str(Path(app.root_path).parent / "content"),
        APPLICATION_VERSION=__version__,
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)
    app.config["SESSION_COOKIE_SECURE"] = bool(app.config["HOSTED_MODE"])
    _validate_hosted_config(app)
    if app.config["HOSTED_MODE"]:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    db.init_app(app)
    app.cli.add_command(validate_content_command)
    app.cli.add_command(content_report_command)
    app.register_blueprint(bp)
    app.before_request(protect_csrf)
    app.before_request(require_hosted_access)
    app.jinja_env.globals["csrf_token"] = csrf_token
    with app.app_context():
        db.init_database()
        lookup = {item["id"]: item for item in load_passages(app.config["CONTENT_PATH"])}
        lookup.update({item["id"]: item for item in lesson_passages()})
        lookup.update({row["id"]: {"text": row["text"], "revision": 1}
                       for row in db.get_db().execute("SELECT id,text FROM custom_passages")})
        db.backfill_key_stats(db.get_db(), {key: item["text"] for key, item in lookup.items()})
        db.backfill_attempt_content(db.get_db(), lookup)
        db.backfill_practice_sessions(db.get_db())
    return app
