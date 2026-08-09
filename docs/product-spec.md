# ScipioTyping product specification

## Purpose

ScipioTyping is a private, offline-first typing tutor for a household. Its first
student is Kenneth, age 12. Practice combines deliberate keyboard instruction
with substantial passages about history, epic literature, mythology, poetry,
chess, world cultures, warfare, leadership, and mathematics.

## Principles

- Accuracy precedes speed; feedback is specific and encouraging.
- The application works without internet, accounts, tracking, or payment.
- All student data belongs to the household and remains on the computer.
- Historical conflict is treated honestly but without graphic detail or
  uncritical glorification.
- Myth, tradition, disputed claims, and documented history are distinguished.
- Parent controls are understandable without programming knowledge.

## Student experience

A student selects a local profile, completes placement or chooses a lesson,
types a passage, receives immediate character-level feedback, and sees WPM,
accuracy, errors, practice time, achievements, and a clearly explained next
recommendation. All primary workflows support keyboard-only use.

## Parent experience

The parent can set goals, manage profiles, control preferred difficulty, preview
content, import validated original passages, export reports, and back up or
restore the complete local database. An optional local PIN discourages casual
access; it is not represented as internet-grade authentication.

## Scoring

- Raw WPM = typed characters / 5 / active minutes.
- The target and submission are aligned before scoring, so one missing character
  does not shift every character that follows it.
- Accuracy = aligned matches / (matches + substitutions + insertions + deletions
  + transpositions) × 100.
- Adjusted WPM = aligned matching characters / 5 / active minutes.
- Active time excludes a pause after 15 seconds without keyboard activity.
- Corrected errors are recorded separately and do not reduce adjusted WPM.

## Personalized practice

- Each completed attempt stores how often each key was expected, matched, or
  missed so accuracy has a meaningful denominator.
- Recent analysis uses the last ten completed attempts and requires at least ten
  uses before rating a key.
- A key is mastered after at least thirty recent uses, 97% accuracy, and no more
  than two errors.
- Weak-key workshops are deterministic, generated from local content, and store
  their target and generator metadata with the result.

## Daily practice time

- Every screen displays active practice today against the selected profile's
  configurable daily goal.
- A practice session starts with the first typed character and pauses after 15
  seconds without keyboard activity.
- Periodic absolute-time updates preserve unfinished-session time without
  double-counting retries.
- The current exercise updates the daily meter immediately; completion reports
  both session time and the updated daily total.
- Daily boundaries follow the computer's local date while timestamps remain UTC.

## Release scope

Version 1.0 includes local profiles, placement, lesson tracks, adaptive passage
recommendations, 60 curated passages, goals, streaks, achievements, trend and
error reports, parent controls, import/export, backup/restore, accessible themes,
offline assets, a Windows launcher, tests, and household documentation.

Version 1.3 adds a multi-file reviewed content system designed for hundreds of
passages, separate typing and reading levels, stable revisions and references,
completion-aware library navigation, and reproducible target storage for every
new result.
