# Data model

- `profiles`: local learners, goals, preferred and placement difficulty.
- `attempts`: one scored practice result, timing, completion, error map, per-key
  evidence, and reproducibility metadata for generated drills.
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

Schema 5 adds `key_stats`, `target_text`, `focus_keys`, and
`generator_version`. New attempts store server-calculated opportunities,
matches, and errors for each expected key. Earlier attempts are backfilled when
their original target is still available; otherwise their per-key evidence
remains unknown. Generated workshops retain their target text, focus keys, and
generator version so a historical result never depends on regenerating content.
