import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_vercel_entry_and_rewrite_are_present():
    configuration = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    assert configuration["rewrites"] == [{"source": "/(.*)", "destination": "/api/index"}]
    entry = (ROOT / "api" / "index.py").read_text(encoding="utf-8")
    assert "app = create_app()" in entry


def test_hosted_dependencies_and_secret_template_are_documented():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    environment = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "psycopg[binary]" in requirements
    for name in ("DATABASE_URL", "SCIPIO_FAMILY_PASSWORD", "SCIPIO_PARENT_PASSWORD",
                 "SCIPIO_KENNETH_PIN", "SCIPIO_WILLIAM_PIN", "SCIPIO_ALICE_PIN"):
        assert name in environment
