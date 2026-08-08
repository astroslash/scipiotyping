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

- Gross WPM = typed characters / 5 / active minutes.
- Accuracy = matching submitted characters / typed characters × 100.
- Net WPM = max(0, gross WPM - uncorrected errors / active minutes).
- Active time excludes a pause after 15 seconds without keyboard activity.
- Corrected errors are recorded separately and do not reduce final net WPM.

## Release scope

Version 1.0 includes local profiles, placement, lesson tracks, adaptive passage
recommendations, 60 curated passages, goals, streaks, achievements, trend and
error reports, parent controls, import/export, backup/restore, accessible themes,
offline assets, a Windows launcher, tests, and household documentation.

