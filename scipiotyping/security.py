from __future__ import annotations

import hmac
import secrets

from flask import abort, current_app, redirect, request, session, url_for


def csrf_token() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(24)
    return session["csrf_token"]


def protect_csrf() -> None:
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
        if not hmac.compare_digest(str(supplied), str(session.get("csrf_token", ""))):
            abort(400, description="The form expired. Return to the page and try again.")


def require_hosted_access():
    """Gate hosted pages first by family password, then by learner PIN."""
    if not current_app.config.get("HOSTED_MODE"):
        return None
    endpoint = request.endpoint or ""
    family_public = {"static", "main.health", "main.family_access"}
    if endpoint in family_public:
        return None
    if not session.get("family_unlocked"):
        return redirect(url_for("main.family_access"))
    profile_public = {
        "main.profiles_page", "main.select_profile", "main.family_logout",
        "main.help_page",
    }
    if endpoint not in profile_public and not session.get("profile_authenticated"):
        return redirect(url_for("main.profiles_page"))
    return None
