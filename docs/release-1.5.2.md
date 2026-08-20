# ScipioTyping 1.5.2 release

Version 1.5.2 fixes the first hosted PostgreSQL initialization. Psycopg invokes
the configured row factory for commands such as `CREATE TABLE`, even though
those commands have no result-column description. The compatibility row factory
now handles that valid case instead of crashing the Vercel function.
