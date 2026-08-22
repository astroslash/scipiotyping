# ScipioTyping 1.11.0

Version 1.11.0 improves symbol-friendly scoring and expands the Elementary
library. Straight and curly quotation marks now compare as the same character,
regardless of direction. In multiplication expressions, `*`, `×`, and `x` also
compare as equivalent. The multiplication rule is context-aware, so replacing
the x in an ordinary word such as “fox” with `*` remains an error.

The release adds fifteen original Grade 3 exercises: five sourced animal
passages, five jokes, and five silly stories. Each is 35–55 words, explicitly
restricted to Elementary profiles, and reviewed for young readers. Elementary
now has 45 passages, Middle School remains at 140, and the complete library has
185 passages.

## Acceptance

- Equivalent characters produce correct live highlighting and 100% server scores.
- Key-error tracking does not record accepted character forms as mistakes.
- Ordinary letter x characters retain exact spelling behavior.
- Each new passage is Level 1, reading Grade 3, and 35–55 words.
- Content validation, automated tests, release checks, and Edge browser checks pass.
