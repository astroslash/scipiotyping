# Developer maintenance guide

ScipioTyping uses Flask 3.1, Waitress, SQLite, Jinja templates, plain CSS, and
plain JavaScript. Selenium drives the installed Microsoft Edge browser for the
release smoke test; it is not a runtime dependency. No front-end build step exists. `create_app` initializes and
migrates the database. Built-in content is listed by `content/manifest.json` and
split across `content/passages/`; custom content lives in SQLite.

Run `run-tests.ps1` before a release. It runs pytest, validates content, opens a
fresh temporary database, checks primary routes and schema integrity, and scans
runtime files for remote dependencies. Never commit `instance/` or `.venv/`.

Schema changes must be added as a new ordered migration in `db.migrate`, must
update the release check's expected version, and must include an upgrade test.
Content changes must retain stable IDs so historical attempts remain readable.
Add new subject files to the manifest, run `flask validate-content`, and regenerate
the inventory with `flask content-report --write-inventory`. Released content uses
the strict schema while Parent-created content uses the household compatibility
schema. Library pagination is fixed at 24 cards per page.

The local Git identity is repository-only: `ScipioTyping Builder` at an invalid
local address. Replace it with your own repository or global identity if desired.
