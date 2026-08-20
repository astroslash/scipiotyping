from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def test_vercel_uses_native_flask_routing_without_a_path_destroying_rewrite():
    assert not (ROOT / "vercel.json").exists()
    configuration = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert configuration["tool"]["vercel"]["entrypoint"] == "api.index:app"
    entry = (ROOT / "api" / "index.py").read_text(encoding="utf-8")
    assert "app = create_app()" in entry


def test_hosted_dependencies_and_secret_template_are_documented():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    environment = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "psycopg[binary]" in requirements
    assert "SCIPIO_FAMILY_PASSWORD" not in environment
    for name in ("DATABASE_URL", "SCIPIO_PARENT_PASSWORD",
                 "SCIPIO_KENNETH_PIN", "SCIPIO_WILLIAM_PIN", "SCIPIO_ALICE_PIN"):
        assert name in environment


def test_distribution_explicitly_packages_code_content_and_assets():
    configuration = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    setuptools = configuration["tool"]["setuptools"]
    assert setuptools["packages"] == ["scipiotyping", "content"]
    assert setuptools["package-data"]["scipiotyping"] == ["templates/*.html", "static/*"]
    assert setuptools["package-data"]["content"] == ["manifest.json", "passages/*.json"]
