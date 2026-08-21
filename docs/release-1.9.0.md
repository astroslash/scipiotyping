# ScipioTyping 1.9.0

Version 1.9.0 makes school level a persistent learner setting. Emily migrates
to Elementary; Kenneth, William, Alice, Guest, existing unnamed learners, and
existing custom passages default to Middle School. Parents must choose
Elementary or Middle School when creating a learner or original passage and
can update the active learner later.

The 30 Grade 3 passages and six young-typist lessons are available only to
Elementary profiles. The 120 advanced passages and eight core keyboard lessons
are available only to Middle School profiles. Filtering covers the home
recommendation, Library and categories, placement, lessons, targeted-practice
sources, direct practice URLs, practice-session creation, and attempt scoring.

Schema 9 stores the selection on profiles and custom passages. The upgrade is
idempotent and preserves all progress, PIN hashes, settings, custom content,
and historical attempts.
