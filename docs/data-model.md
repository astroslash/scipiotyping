# Data model

- `profiles`: learners, goals, preferred and placement difficulty, active state,
  and an optional one-way learner PIN hash.
- `attempts`: one scored practice result, timing, completion, error map, per-key
  evidence, and reproducibility metadata for generated drills.
- `practice_sessions`: active typing time for completed and unfinished exercises,
  linked to an attempt when one is completed.
- `practice_time_segments`: monotonic heartbeat deltas timestamped for accurate
  local-day totals, including sessions that cross midnight.
- `achievements`: unique milestones earned by a profile.
- `custom_passages`: parent-created original passages stored in the active database.
- `settings`: household settings, including optional PIN hash and UI defaults.
- `schema_version`: the most recently applied database migration.

`profiles` owns `attempts` and `achievements`. The parent interface deactivates
profiles so accidental removal remains recoverable; a true database deletion
would cascade to both related tables. Built-in passages live in validated JSON and are immutable at runtime.
Custom passages use the same public representation and are included in local
database backups or hosted JSON archives.

Migrations are ordered, idempotent operations executed during application
startup. A migration test opens a version-one database and confirms upgrade
without loss of the original profile or attempts.

Schema 5 adds `key_stats`, `target_text`, `focus_keys`, and
`generator_version`. New attempts store server-calculated opportunities,
matches, and errors for each expected key. Earlier attempts are backfilled when
their original target is still available; otherwise their per-key evidence
remains unknown. Generated workshops retain their target text, focus keys, and
generator version so a historical result never depends on regenerating content.

Schema 6 adds `practice_sessions` and `practice_time_segments`. The browser
reports an absolute active-time total periodically, making retries idempotent;
only the positive delta becomes a timestamped segment. A session belongs to one
profile and is linked to its completed attempt without counting time twice.
Historical attempts are represented as completed sessions exactly once. Daily
totals use UTC timestamps bounded by midnight in the computer's local timezone.

Schema 7 adds `passage_revision` to attempts and stores `target_text` for every
new result. On upgrade, historical attempts are backfilled only when their
passage is still known. Unknown passage targets remain null rather than being
guessed. This keeps scoring history reproducible when built-in content is later
corrected or revised.

Schema 8 adds `profiles.pin_hash`. The SQLite migration leaves it empty because
local profiles remain frictionless. Hosted startup stores Werkzeug password
hashes for saved-learner PINs supplied through environment variables or Emily's
built-in initial PIN. Plain PINs and the parent password are never stored in the
database or exports.
