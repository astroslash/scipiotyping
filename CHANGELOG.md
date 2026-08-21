# Changelog

## 1.8.0 — 2026-08-20

- Added Emily as a saved Level 1 learner with a 10-minute daily goal and initial
  PIN `3333`.
- Added six optional young-typist lessons with simple animal humor and stories.
- Added 30 reviewed Grade 3 passages across Animals, Kid Jokes, and Silly
  Stories, bringing the built-in library to 150 passages in 13 subjects.
- Added a young-reader home collection for Emily and other Level 1 learners.

## 1.7.0 — 2026-08-20

- Added a PIN-protected Guest practice option without creating a database
  profile or saving attempts, practice time, achievements, or placement.
- Kept exercise scoring available in Guest mode and clearly labeled results as
  temporary throughout the interface.

## 1.6.1 — 2026-08-19

- Made the public app address clear any remembered learner and open the learner
  chooser every time, while keeping ordinary in-app Home navigation signed in.

## 1.6.0 — 2026-08-19

- Removed the shared family password so hosted visitors arrive directly at the
  learner chooser; learner PINs and the separate Parent password remain.
- Made welcome headings responsive and resistant to word clipping through 200%
  browser zoom.

## 1.5.4 — 2026-08-19

- Removed the obsolete catch-all Vercel rewrite that changed every incoming
  Flask path to `/api/index` and caused `/access` to redirect to itself.
- Declared the WSGI entry point through Vercel's native Flask configuration so
  `/access`, `/health`, and all application routes preserve their original paths.

## 1.5.3 — 2026-08-19

- Stopped hosted startup from creating the offline SQLite instance directory on
  Vercel's read-only `/var/task` filesystem.
- Kept local directory and secret-file creation unchanged for offline Windows use.

## 1.5.2 — 2026-08-19

- Fixed PostgreSQL startup when schema-creation commands return no result-column
  description, which previously crashed the first Vercel function invocation.
- Added regression coverage for PostgreSQL commands that do not return rows.

## 1.5.1 — 2026-08-19

- Declared the application and content packages explicitly so Vercel's locked
  `uv` build no longer rejects the repository's flat layout.
- Included the Jinja templates, browser assets, manifest, and all passage JSON
  files in the built wheel so hosted installs retain the complete application.

## 1.5.0 — 2026-08-19

- Added William and Alice alongside Kenneth as idempotently seeded learners.
- Added optional learner PINs, a family password gate, and a separate parent
  password for private hosted use without child accounts or email addresses.
- Added dual database support: SQLite remains the offline default while hosted
  deployments use PostgreSQL through `DATABASE_URL`.
- Added Vercel packaging, secure hosted configuration validation, and a guarded
  SQLite-to-PostgreSQL migration utility for existing progress.
- Added hosted JSON backups while retaining complete SQLite backup and restore
  in offline mode; credential hashes are excluded from hosted exports.
- Added hosted-mode, profile isolation, deployment configuration, migration,
  and offline regression coverage.

## 1.4.1 — 2026-08-09

- Added the running application version to the local health check.
- Updated the Windows launcher to distinguish the current release from a stale
  ScipioTyping server left running after an upgrade.
- Restart only a verified ScipioTyping listener when its version is old, and
  refuse to stop unrelated programs that happen to use port 5000.

## 1.4.0 — 2026-08-09

- Doubled the reviewed built-in library from 60 to 120 passages.
- Added six original, source-backed passages to each of the ten existing
  subjects without changing any v1.3 passage object.
- Expanded advanced practice with 25 new Level 4 and 15 new Level 5 passages,
  while adding 5 Level 2 and 15 Level 3 passages for a balanced path.
- Added age-aware word bands, original-rights metadata, review dates,
  vocabulary support, context notes, and structured HTTPS references.
- Protected all 120 released passage IDs and added regression checks for exact
  category counts, difficulty distribution, word bands, rights, and sources.
- Updated the generated inventory, content guidance, release documentation, and
  browser-tested offline release package.

## 1.3.0 — 2026-08-09

- Split the built-in library into ten independently maintainable subject files.
- Added content schema 2 with reading level, typing focus, revision, review, and
  structured reference metadata.
- Added strict release validation, legacy-ID protection, near-duplicate warnings,
  content reports, and generated inventory documentation.
- Added per-profile completed and unpracticed filters, completion badges, sorting,
  estimated practice time, and 24-item library pagination.
- Added schema migration 7 so every new result preserves its exact target text and
  passage revision; known historical targets are backfilled without losing data.
- Added multi-file, 500-passage, metadata, navigation, profile, revision, and
  migration regression coverage.

## 1.2.0 — 2026-08-08

- Added a persistent daily practice meter to every screen.
- Added active-time practice sessions with idempotent periodic heartbeats.
- Preserved time from unfinished exercises while excluding long inactivity.
- Added local-day goal calculations and live 15-minute goal feedback.
- Linked completed sessions to attempts without double-counting time.
- Added practice-time CSV/JSON exports and reset/backup integration.
- Added schema migration 6 with historical attempt backfill.
- Added timing, timezone-boundary, profile-isolation, API, UI, and Edge tests.

## 1.1.0 — 2026-08-08

- Added server-authoritative per-key opportunities, matches, errors, and accuracy.
- Added recent and all-time key analysis with weak, developing, and mastered states.
- Added an accessible keyboard heatmap that does not rely on color alone.
- Added deterministic, offline weak-key workshops assembled from local content.
- Added focus-key results, mastery feedback, and two focused-practice achievements.
- Added schema migration 5 with reproducible generated targets and focus metadata.
- Added migration, scoring, aggregation, generation, route, and Microsoft Edge tests.

## 1.0.1 — 2026-08-08

- Replaced slot-by-slot scoring with character-sequence alignment.
- Added separate substitution, insertion, deletion, and transposition counts.
- Added raw WPM, accuracy, and alignment-based adjusted WPM.
- Added alignment-aware live highlighting and corrected expected-key tracking.
- Added automatic end detection that tolerates missing interior characters.
- Added a character progress counter and an 85% `Finish and score` fallback.
- Added an accessible aligned result view and detailed error breakdown.
- Added schema migration 4 while preserving existing progress and WPM history.
- Added missing-space, skipped-letter, insertion, substitution, transposition,
  repeated-text, automatic-completion, and manual-fallback regression tests.

## 1.0.0 — 2026-08-08

- Added offline browser-based typing practice with server-authoritative scoring.
- Added 60 educational passages and eight focused keyboard lessons.
- Added placement, progression, adaptive recommendations, goals, streaks,
  achievements, weak-key analysis, trends, and printable reports.
- Added multiple local profiles and optional hashed parent PIN protection.
- Added custom passages, CSV/JSON export, backup, validated restore, and reset.
- Added responsive, reduced-motion, high-contrast, large-text, and print styles.
- Added database migrations, Windows launcher, documentation, and test suite.
