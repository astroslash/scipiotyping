# Troubleshooting

## The browser does not open

Keep the PowerShell window open and visit `http://127.0.0.1:5000` manually. If
the window shows that port 5000 is already in use, another copy may be running.
The launcher checks the running ScipioTyping version and restarts an older copy
after an upgrade. It will not stop an unrelated program using port 5000.

## The Library says something went wrong after an upgrade

Close any old ScipioTyping PowerShell windows and run the shortcut again. Since
v1.4.1 the launcher detects this condition automatically. Saved progress is in
`instance/scipiotyping.db` and is not removed during a server restart.

## PowerShell will not run the launcher

Run `.\.venv\Scripts\python.exe -m scipiotyping` from this directory. If `.venv`
does not exist, follow the developer setup commands in the README.

## A result will not save

Confirm the local server window is running. Return to the Library and retry. A
browser page left open after the server stops cannot write to the database.

## The database has a problem

Do not delete it. Copy the entire `instance` directory somewhere safe, then use
a known-good backup through Parent → Restore. Automatic pre-restore copies are
kept under `instance/backups`.
