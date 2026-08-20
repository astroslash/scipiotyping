# ScipioTyping 1.5.4 release

Version 1.5.4 fixes hosted route handling. The previous catch-all Vercel rewrite
replaced the request path with `/api/index`, so the family-access gate could not
recognize `/access` or `/health` and redirected every request back to `/access`.
The release uses Vercel's native Flask entry-point support, which passes the
original browser path to Flask without a manual rewrite.
