# Release checklist — 1.9.0

## 1.9.0

- [x] Added and migrated Elementary/Middle School profile assignments.
- [x] Enforced audience filtering in UI, direct practice, session, and scoring paths.
- [x] Added school-level selection to learner and custom-passage Parent forms.
- [x] Preserved a pre-schema-9 backup of Kenneth's local database.
- [x] Full release suite, browser checks, commit, tag, and GitHub push completed.

## 1.8.0

- [x] Seeded Emily with PIN 3333, Level 1, and a 10-minute daily goal.
- [x] Added and reviewed 30 Grade 3 passages in three young-reader subjects.
- [x] Added six optional young-typist lessons without changing core progression.
- [x] Full release suite, browser checks, commit, tag, and GitHub push completed.

## 1.7.0

- [x] Added the hardcoded Guest PIN and a session-only Guest learner.
- [x] Confirmed Guest scoring writes no profile, attempt, time, or achievement data.
- [x] Full release suite, browser checks, commit, tag, and GitHub push completed.

## 1.6.1

- [x] Made every visit to the public root URL start with no selected learner.
- [x] Kept the signed-in learner dashboard at a separate in-app Home URL.
- [x] Full release suite, browser checks, commit, tag, and GitHub push completed.

## 1.6.0

- [x] Removed the shared family password and retained learner PIN protection.
- [x] Made welcome headings wrap without clipping at browser zoom up to 200%.
- [x] Full release suite, browser checks, commit, tag, and GitHub push completed.

## 1.5.4

- [x] Reproduced the redirect loop against `/access` and `/health` in production.
- [x] Removed the path-destroying catch-all rewrite and selected native Flask routing.
- [x] Full release suite, wheel inspection, commit, tag, and GitHub push completed.

## 1.5.3

- [x] Identified the read-only `/var/task/instance` failure from Vercel logs.
- [x] Restricted instance-directory creation to persistent local mode.
- [x] Full release suite, wheel inspection, commit, tag, and GitHub push completed.

## 1.5.2

- [x] Traced the post-build function crash into PostgreSQL DDL row handling.
- [x] Made the PostgreSQL row factory accept commands without result columns.
- [x] Full release suite, version commit, tag, and GitHub push completed.

## 1.5.1

- [x] Reproduced Vercel's setuptools flat-layout package discovery failure.
- [x] Explicitly packaged only the application and offline content library.
- [x] Inspected a clean wheel for Python code, templates, static assets, and all content files.
- [x] Full release suite, version commit, tag, and GitHub push completed.

## 1.5.0

- [x] Preserved a pre-migration copy of Kenneth's local database.
- [x] Migrated the live local database to schema 8 with all 67 attempts intact.
- [x] Seeded Kenneth, William, and Alice while preserving offline profile behavior.
- [x] Added private hosted family, learner, and parent access layers.
- [x] Added PostgreSQL, Vercel, JSON archive, and guarded migration support.
- [x] Added deployment and parent documentation without committing credentials.
- [x] Full unit, content, release, offline Edge, and hosted Edge checks completed.
- [x] Version 1.5.0 commit, tag, and GitHub push completed.

## 1.4.1

- [x] Reproduced the Library error against the stale August 8 server.
- [x] Confirmed the current code serves Kenneth's unchanged database correctly.
- [x] Added version reporting and version-aware Windows launcher restart logic.
- [x] Verified the launcher refuses to terminate an unrelated port-5000 process.
- [x] Exercised the real stale-server upgrade path and Library page in Edge.
- [x] Full release command completed; version committed, tagged, and pushed.

## 1.4.0

- [x] Pre-release database backup created and v1.3.0 baseline verified.
- [x] Editorial gap analysis and source plan completed across ten subjects.
- [x] Sixty reviewed passages added in three batches without changing v1.3 objects.
- [x] Every subject now contains 12 passages and all 120 IDs are protected.
- [x] Planned difficulty distribution and Level 2–5 word bands tested.
- [x] Rights, references, age suitability, vocabulary, and uncertainty reviewed.
- [x] Full release command and Microsoft Edge workflow completed.
- [x] Version 1.4.0 committed, tagged, and pushed.

## 1.3.0

- [x] Pre-release database backup created and v1.2.0 baseline verified.
- [x] Content schema 2, manifest, and ten subject files implemented.
- [x] All 60 legacy IDs preserved with reviewed metadata.
- [x] Validation, reporting, inventory generation, and 500-item loading tested.
- [x] Profile-specific completion filters, sorting, badges, and pagination added.
- [x] Passage target and revision migration 7 implemented and tested.
- [x] Full release command completed.
- [x] Version 1.3.0 committed, tagged, and pushed.

## 1.2.0

- [x] Practice-session schema migration 6 and historical backfill implemented.
- [x] Profile-owned, idempotent active-time heartbeats implemented.
- [x] Local-day summary and configurable goal calculation tested.
- [x] Daily meter displayed across all primary screens.
- [x] Live session and daily progress verified in Microsoft Edge.
- [x] Abandoned session, export, reset, backup, and restore behavior covered.
- [x] Full release command completed.
- [x] Version 1.2.0 committed, tagged, and pushed.

## 1.1.0

- [x] Per-key evidence and schema migration 5 implemented.
- [x] Weak, developing, and mastered classifications unit tested.
- [x] Accessible keyboard heatmap added.
- [x] Deterministic offline targeted drills and reproducible storage added.
- [x] Focus-key feedback and achievements added.
- [x] Full release command completed.
- [x] Version 1.1.0 committed, tagged, and pushed.

## 1.0.1

- [x] Alignment scoring implemented and unit tested.
- [x] Existing progress preserved through schema migration 4.
- [x] Automatic imperfect-passage completion verified in Microsoft Edge.
- [x] Manual finish fallback verified in Microsoft Edge.
- [x] Raw WPM, adjusted WPM, accuracy, and error types displayed.
- [x] Full release command completed.
- [x] Version 1.0.1 committed, tagged, and pushed.

## 1.0.0

- [x] Python 3.14 virtual environment created.
- [x] Runtime and test dependencies pinned and installed.
- [x] Existing prototype preserved in Git.
- [x] Product, user, data, content, and screen specifications written.
- [x] Sixty built-in passages validate across ten categories.
- [x] Versioned schema migration and data-preservation test added.
- [x] Core routes, scoring, profiles, parent tools, and recovery tested.
- [x] Local assets contain no remote runtime dependency.
- [x] Windows production launcher uses Waitress on localhost.
- [x] Final browser walkthrough completed at desktop and compact widths.
- [x] Real Edge exercise completed, corrected, scored, and saved without console errors.
- [x] Final full release command completed.
- [x] Version 1.0.0 commit and tag created.
