# ScipioTyping

ScipioTyping is a private, offline-first typing tutor built for Kenneth. It runs
in a web browser, stores progress in a local SQLite database, and uses no cloud
accounts, advertisements, analytics, CDNs, or subscriptions.

## Windows setup

Open PowerShell in this directory and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m scipiotyping init-db
python -m scipiotyping
```

Then open `http://127.0.0.1:5000`. Press `Ctrl+C` in PowerShell to stop it.
After installation, `start-scipiotyping.ps1` provides a one-command launcher.

## Tests and content checks

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m scipiotyping validate-content
```

## Privacy and backups

All progress is stored in `instance/scipiotyping.db`. The parent dashboard can
download JSON/CSV exports and create or restore local backups. Keep backups in
a safe place before moving or upgrading the computer.

See `docs/parent-guide.md` and `docs/developer-guide.md` for more detail.

