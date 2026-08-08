"""ScipioTyping application factory."""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask

from . import db
from .content import validate_content_command
from .routes import bp


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "local-development-only"),
        DATABASE=os.environ.get("SCIPIO_DATABASE", str(Path(app.instance_path) / "scipiotyping.db")),
        CONTENT_PATH=str(Path(app.root_path).parent / "content" / "passages.json"),
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    app.cli.add_command(validate_content_command)
    app.register_blueprint(bp)
    with app.app_context():
        db.init_database()
    return app
