# ScipioTyping 1.5.1 release

Version 1.5.1 fixes the first Vercel build of v1.5.0. Setuptools no longer
attempts ambiguous automatic discovery across the repository's `api`, `content`,
and `scipiotyping` directories. The distribution explicitly contains the
ScipioTyping package and packaged content library, including every template,
static browser asset, manifest, and passage file.
