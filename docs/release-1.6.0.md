# ScipioTyping 1.6.0

Version 1.6.0 removes the shared family-password step from hosted mode. A hosted
visitor now arrives at the learner chooser and must enter Kenneth's, William's,
or Alice's PIN before any learner data is shown. The separate Parent password
continues to protect settings, exports, backups, and profile management.

The welcome eyebrow and home hero now use responsive, balanced headings that do
not split words or clip lines as browser zoom changes. Automated Edge coverage
checks both welcome views from 100% through 200% zoom.

`SCIPIO_FAMILY_PASSWORD` is no longer read or required and may be deleted from
Vercel. No database migration is required; schema 8 and all existing progress
remain unchanged.
