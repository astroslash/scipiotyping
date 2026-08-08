# ScipioTyping 1.0.1 release verification

Version 1.0.1 corrects passage completion and introduces alignment-based scoring.

- Character sequence alignment recognizes matches, substitutions, insertions,
  deletions, and adjacent transpositions.
- A missing letter or space produces one local error rather than shifting the
  remainder of the passage.
- Automatic completion uses length and ending similarity, with a short debounce.
- A manual finish control becomes available at 85% completion.
- Raw and adjusted WPM, alignment accuracy, corrections, and remaining errors are
  reported separately.
- Database migration 4 backfills adjusted WPM from prior net-WPM records.

Verification requires `run-tests.ps1`, including the real Microsoft Edge smoke
test for a perfect corrected attempt, automatic completion with an omitted
character, and manual fallback completion.
