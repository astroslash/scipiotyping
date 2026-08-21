# ScipioTyping 1.8.0

Version 1.8.0 adds Emily as the fourth saved learner. Her initial PIN is `3333`,
her preferred difficulty is Level 1, and her daily goal begins at 10 minutes.
The PIN can later be overridden with `SCIPIO_EMILY_PIN` without changing code.

The Lessons screen now begins with six optional young-typist exercises featuring
cats, dogs, ducks, monkeys, penguins, and a silly animal parade. These exercises
do not add requirements to the existing keyboard-level progression.

The built-in library grows from 120 to 150 passages. The 30 additions are Grade
3, Level 1 texts: 10 animal facts, 10 kid jokes, and 10 original silly stories.
Each is 35–55 words, reviewed for age suitability, and available to every
learner. Level 1 profiles receive direct links to the collection from Home.

No database schema migration is required. Startup adds Emily idempotently while
preserving every existing learner and result.
