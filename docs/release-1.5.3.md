# ScipioTyping 1.5.3 release

Version 1.5.3 fixes hosted startup on Vercel's read-only application filesystem.
The application now creates its `instance` directory and local secret file only
in offline mode. Hosted mode uses its configured PostgreSQL database and Vercel
environment secret without attempting to write beneath `/var/task`.
