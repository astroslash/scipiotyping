"""Fast, deterministic release checks that require no network connection."""
from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from scipiotyping import __version__, create_app
from scipiotyping.content import load_passages, render_inventory, validate_passages
from scipiotyping.db import SCHEMA_VERSION, get_db


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as temporary:
        app = create_app({"TESTING": True, "SECRET_KEY": "release-check", "DATABASE": str(Path(temporary) / "release.db")})
        items = load_passages(app.config["CONTENT_PATH"])
        assert not validate_passages(items, strict=True)
        assert len(items) >= 60
        manifest = json.loads((root / "content" / "manifest.json").read_text(encoding="utf-8"))
        assert set(manifest["legacy_ids"]).issubset({item["id"] for item in items})
        assert (root / "docs" / "content-inventory.md").read_text(encoding="utf-8") == render_inventory(items)
        with app.test_client() as client:
            for route in ("/", "/health", "/library", "/lessons", "/placement", "/progress", "/profiles", "/parent", "/help"):
                response = client.get(route)
                assert response.status_code == 200, f"{route}: {response.status_code}"
        with app.app_context():
            assert get_db().execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert get_db().execute("SELECT version FROM schema_version").fetchone()[0] == SCHEMA_VERSION
    remote = re.compile(r"(?:src|href)=[\"']https?://|@import\s+url\(https?://", re.I)
    for folder in (root / "scipiotyping" / "templates", root / "scipiotyping" / "static"):
        for path in folder.rglob("*"):
            if path.is_file():
                assert not remote.search(path.read_text(encoding="utf-8")), f"Remote runtime dependency in {path}"
    print(f"ScipioTyping {__version__}: release checks passed ({len(items)} passages, schema {SCHEMA_VERSION}, offline assets).")


if __name__ == "__main__":
    main()
