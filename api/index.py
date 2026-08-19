"""WSGI entry point used by Vercel's Python runtime."""

from scipiotyping import create_app

app = create_app()
