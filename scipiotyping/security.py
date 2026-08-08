from __future__ import annotations

import hmac
import secrets

from flask import abort, request, session


def csrf_token() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(24)
    return session["csrf_token"]


def protect_csrf() -> None:
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
        if not hmac.compare_digest(str(supplied), str(session.get("csrf_token", ""))):
            abort(400, description="The form expired. Return to the page and try again.")

