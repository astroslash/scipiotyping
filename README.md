# ScipioTyping

ScipioTyping is a private, offline-first typing tutor for Kenneth, William,
Alice, and Emily. It runs in a browser with no advertisements, analytics, CDN, or paid
subscription. Local mode stores progress in SQLite; hosted mode uses PostgreSQL
so the family can share one private Vercel deployment.

A PIN-protected Guest option scores exercises without storing attempts,
practice time, achievements, or a database profile.

Each saved learner is assigned to Elementary or Middle School. Emily receives
the 45 Grade 3 passages and six young-typist lessons; Kenneth, William, Alice,
and Guest receive the 140 more advanced passages and the core keyboard path.
Parents choose the school level when creating a profile and can change it later.

## Start on Windows

Right-click `start-scipiotyping.ps1` and choose **Run with PowerShell**, or open
PowerShell in this folder and run:

```powershell
.\start-scipiotyping.ps1
```

The first run creates `.venv` and installs the required Python packages.
Later launches work offline. The browser opens to the learner chooser at
`http://127.0.0.1:5000`.
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
changes `SCIPIO_HOST`. Hosted mode requires separate learner PINs, a separate
parent password, HTTPS cookies, and a PostgreSQL `DATABASE_URL`.
No child email addresses or third-party sign-ins are needed. See the [Vercel
deployment guide](docs/vercel-deployment.md), [Parent guide](docs/parent-guide.md),
[Developer guide](docs/developer-guide.md), and
[Troubleshooting](docs/troubleshooting.md).

The 185 built-in passages are organized into thirteen subjects under
`content/passages` and remain available offline. The Library can filter
completed or unpracticed passages, sort the collection, and page through it.
School-level filtering is enforced in the Library, lessons, recommendations,
direct practice links, and scoring endpoints.

Typing feedback accepts straight and curly quotation marks interchangeably. In
multiplication expressions, `*`, `×`, and `x` are accepted as equivalent forms.
