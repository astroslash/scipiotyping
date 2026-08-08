# ScipioTyping

ScipioTyping is a private, offline-first typing tutor made for Kenneth. It runs
in a browser, stores progress in a local SQLite database, and uses no cloud
account, advertisement, analytics service, CDN, or subscription.

## Start on Windows

Right-click `start-scipiotyping.ps1` and choose **Run with PowerShell**, or open
PowerShell in this folder and run:

```powershell
.\start-scipiotyping.ps1
```

The first run creates `.venv` and installs the two required Python packages.
Later launches work offline. The browser opens to `http://127.0.0.1:5000`.
Leave the PowerShell window open while using the app; press `Ctrl+C` there to
stop it.

If PowerShell blocks local scripts, use this equivalent command:

```powershell
.\.venv\Scripts\python.exe -m scipiotyping
```

## Developer setup

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m flask --app scipiotyping init-db
.\run-tests.ps1
```

## Data and privacy

Progress, profiles, preferences, achievements, and custom passages are stored in
`instance/scipiotyping.db`. A locally generated secret protects browser sessions.
The Parent dashboard downloads CSV/JSON reports and complete SQLite backups.
Restore automatically preserves the previous database under `instance/backups`.

The server binds only to `127.0.0.1` unless a knowledgeable user deliberately
changes `SCIPIO_HOST`. See [Parent guide](docs/parent-guide.md), [Developer
guide](docs/developer-guide.md), and [Troubleshooting](docs/troubleshooting.md).
