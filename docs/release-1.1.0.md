# ScipioTyping 1.1.0 release verification

Version 1.1.0 adds personalized weak-key training while preserving the private,
offline-first design.

- Server-authoritative scoring stores opportunities, matches, and errors by key.
- Progress presents recent accuracy through an accessible keyboard heatmap.
- Weak keys require sufficient evidence and mastered keys require sustained high
  accuracy rather than a single result.
- Focused workshops are deterministic and assembled only from local content.
- Generated targets, focus keys, and generator versions remain with attempts.
- Existing attempts receive best-effort evidence only when their target remains
  available; unavailable history is not guessed.

Verification requires `run-tests.ps1`, including migration, analysis,
generation, targeted-route, accessibility-markup, and real Microsoft Edge flow
checks.
