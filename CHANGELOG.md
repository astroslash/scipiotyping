# Changelog

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
