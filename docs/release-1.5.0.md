# ScipioTyping 1.5.0 release

Version 1.5.0 adds the William and Alice learner profiles and makes the same app
safe to deploy for private family use. Offline Windows use remains the default
and preserves the existing SQLite history. Hosted mode requires PostgreSQL and
layers a family password, learner-specific PINs, and a separate parent password
over the existing CSRF and signed-session protections.

The release includes a guarded one-time data migration, credential-free JSON
archives for hosted data, Vercel configuration, and deployment documentation.
No learner email, advertising service, analytics script, CDN, or paid feature is
introduced.
