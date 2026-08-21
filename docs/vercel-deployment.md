# Deploying ScipioTyping to Vercel

ScipioTyping keeps the Windows shortcut and local SQLite data unchanged.
The hosted copy uses PostgreSQL because Vercel functions do not provide a
persistent SQLite filesystem. A free Vercel Hobby project plus a free PostgreSQL
provider such as Neon is sufficient for normal family use; no paid subscription
is built into ScipioTyping.

## 1. Create private credentials

Choose and keep these outside GitHub:

- `SECRET_KEY`: at least 32 random characters.
- `SCIPIO_PARENT_PASSWORD`: a password of at least 12 characters.
- `SCIPIO_KENNETH_PIN`, `SCIPIO_WILLIAM_PIN`, and `SCIPIO_ALICE_PIN`: three
  distinct PINs of 4–10 digits.
- `SCIPIO_EMILY_PIN` is optional. Emily's requested initial PIN is built in as
  `3333`; set this variable only to override it privately.

PowerShell can generate a suitable session secret:

```powershell
[Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLower()
```

## 2. Create PostgreSQL

Create a PostgreSQL database (the Neon integration in Vercel's Storage or
Marketplace area is one option). Save its pooled connection string, including
`sslmode=require`, as `DATABASE_URL`. Never paste the value into a tracked file.

## 3. Import the GitHub repository

In Vercel, choose **Add New → Project**, import
`astroslash/scipiotyping`, and leave the framework preset on **Other**. The root
directory is the repository root. Add the five credential variables from step 1
plus `DATABASE_URL`—six values total—for Production, Preview, and Development.
Deploy.

`api/index.py` is the serverless WSGI entry point. Vercel's native Flask routing
sends each original URL to it without a catch-all rewrite. A successful
deployment's `/health` endpoint reports version `1.9.0` (or later) and schema `9`.

## 4. Copy existing local progress once

First make another Parent-dashboard backup. Then expose the new PostgreSQL
connection and the five access credentials only in the current PowerShell
window, and run:

```powershell
$env:DATABASE_URL = "postgresql://..."
$env:SECRET_KEY = "..."
$env:SCIPIO_PARENT_PASSWORD = "..."
$env:SCIPIO_KENNETH_PIN = "..."
$env:SCIPIO_WILLIAM_PIN = "..."
$env:SCIPIO_ALICE_PIN = "..."
\.venv\Scripts\python.exe scripts\migrate_sqlite_to_postgres.py instance\scipiotyping.db
```

The migration refuses to write if the hosted database already contains progress
data or profile IDs do not align. It does not copy local parent credentials and
keeps the learner PIN hashes generated from the hosted environment values.
Remove the temporary environment values by closing that PowerShell window.

## 5. Verify and operate

Visit the Vercel URL in a private browser window. Confirm the welcome screen,
all saved-learner PINs, Emily's PIN `3333`, Guest PIN `8675309`, the separate Parent password,
Kenneth's historical results, and one new completed lesson. Confirm a Guest
exercise is scored and labeled as not saved. Download an occasional hosted JSON archive
from Parent. Use the database provider's restore/snapshot tools for a full cloud
restore. The local shortcut continues to work offline against the original
SQLite database.
