# Data model

- `profiles`: local learners, goals, preferred and placement difficulty.
- `attempts`: one scored practice result, timing, completion, and error map.
- `achievements`: unique milestones earned by a profile.
- `custom_passages`: parent-imported passages stored locally.
- `settings`: household settings, including optional PIN hash and UI defaults.
- `schema_version`: the most recently applied database migration.

`profiles` owns `attempts` and `achievements`. The parent interface deactivates
profiles so accidental removal remains recoverable; a true database deletion
would cascade to both related tables. Built-in passages live in validated JSON and are immutable at runtime.
Custom passages use the same public representation but remain in SQLite so a
database backup contains all household-created material.

Migrations are ordered, idempotent operations executed during application
startup. A migration test opens a version-one database and confirms upgrade
without loss of the original profile or attempts.
