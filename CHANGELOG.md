# Changelog

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
