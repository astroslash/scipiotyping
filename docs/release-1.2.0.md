# ScipioTyping 1.2.0 release verification

Version 1.2.0 makes Kenneth's daily 15-minute practice goal continuously visible
and preserves active typing time across completed and unfinished exercises.

- A persistent header meter shows today's active time on every primary screen.
- The exercise timer is labeled as the current session and updates the daily
  meter immediately.
- Profile-owned sessions receive monotonic absolute heartbeats, so retries cannot
  double-count time and abandoned exercises retain recent saved activity.
- Inactivity beyond 15 seconds remains excluded from active time.
- Daily totals use local-midnight boundaries and configurable profile goals.
- Timestamped heartbeat segments divide sessions correctly when typing crosses
  local midnight.
- Historical attempts migrate to completed sessions exactly once.
- Parent exports include dedicated practice-time CSV and JSON reports.

Verification requires `run-tests.ps1`, including schema migration, local-day
boundaries, profile isolation, heartbeat validation, persistent UI markup, live
completion updates, and the complete Microsoft Edge exercise flow.
