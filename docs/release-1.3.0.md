# ScipioTyping 1.3.0 release verification

Version 1.3.0 prepares ScipioTyping to expand from 60 passages to hundreds while
preserving Kenneth's existing progress and every historical passage ID.

- Content schema 2 adds typing focus, reading grade, revision, release, review,
  and structured reference metadata.
- A manifest loads ten independent subject files and protects all 60 legacy IDs.
- Validation detects malformed metadata, duplicate IDs, duplicate text, unsafe
  manifest paths, and unreviewed release content; the report also warns about
  likely near-duplicates.
- The generated inventory reports subject, difficulty, reading-level, rights,
  review, and word-count coverage.
- The Library provides profile-specific completion badges and status filters,
  six sort modes, estimated practice time, reset controls, and 24-card pages.
- Schema 7 stores exact target text and passage revision for every new result and
  backfills known historical targets without inventing unknown data.
- Built-in and household content retain separate validation policies.

Release verification runs unit and integration tests, strict content validation,
inventory freshness checks, fresh and upgraded database checks, offline asset
inspection, and the complete Microsoft Edge typing workflow.
