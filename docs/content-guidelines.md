# Content guidelines

Built-in passages use content schema 2. Every passage requires an identifier,
title, text, category, typing difficulty (1–5), minimum age, reading grade,
educational objectives, typing focus, context, vocabulary, source note, rights
status, revision, introduction version, review status, review date, and at least
one structured reference.

- Keep identifiers permanent. Never reuse or remove an ID listed in
  `content/manifest.json`; historical attempts depend on it.
- Increment `revision` whenever target text changes. Metadata-only corrections do
  not require a revision increase.
- Write original explanations or adapt genuinely public-domain material.
- Do not reproduce modern translations, articles, or poems without permission.
- Label myth and legendary tradition as such.
- Identify uncertain or disputed historical details.
- Avoid graphic descriptions, triumphalism, and claims that conquest alone is
  greatness. Include consequences and multiple causes where relevant.
- Explain unfamiliar vocabulary without speaking down to a 12-year-old.
- Represent cultures as internally varied rather than as stereotypes.
- Verify names, dates, punctuation, and factual claims before marking reviewed.
- Mathematical explanations must distinguish intuition from proof.
- Keep released passages between 35 and 220 words. Vary length intentionally,
  using longer text primarily at higher typing levels.

Run `python -m flask --app scipiotyping validate-content` after editing and
`python -m flask --app scipiotyping content-report --write-inventory` before a
release. Drafts stay outside the manifest until they have passed factual,
age-suitability, rights, punctuation, and typing review.

Imported household passages receive `rights: original` and a source note chosen
by the parent. They use a smaller compatibility schema because they are private
and are stored in SQLite. ScipioTyping validates format but cannot establish
legal rights or historical truth automatically.
