from __future__ import annotations

import csv
import io
import json
import sqlite3
from datetime import UTC, datetime, timedelta

from flask import Blueprint, Response, abort, current_app, jsonify, render_template, request

from .content import load_passages, validate_passages
from .db import get_db
from .scoring import calculate_score

bp = Blueprint("main", __name__)


def passages() -> list[dict]:
    return load_passages(current_app.config["CONTENT_PATH"])


def selected_profile():
    return get_db().execute("SELECT * FROM profiles ORDER BY id LIMIT 1").fetchone()


@bp.get("/health")
def health():
    get_db().execute("SELECT 1").fetchone()
    return jsonify(status="ok", application="ScipioTyping")


@bp.get("/")
def index():
    profile = selected_profile()
    stats = get_db().execute(
        "SELECT COUNT(*) attempts, COALESCE(ROUND(AVG(net_wpm),1),0) wpm, "
        "COALESCE(ROUND(AVG(accuracy),1),0) accuracy FROM attempts WHERE profile_id=?",
        (profile["id"],),
    ).fetchone()
    return render_template("index.html", profile=profile, stats=stats, passage_count=len(passages()))


@bp.get("/library")
def library():
    category = request.args.get("category", "")
    difficulty = request.args.get("difficulty", type=int)
    items = passages()
    if category:
        items = [item for item in items if item["category"] == category]
    if difficulty:
        items = [item for item in items if item["difficulty"] == difficulty]
    return render_template(
        "library.html", passages=items, categories=sorted({p["category"] for p in passages()}),
        selected_category=category, selected_difficulty=difficulty,
    )


@bp.get("/practice/<passage_id>")
def practice(passage_id: str):
    passage = next((item for item in passages() if item["id"] == passage_id), None)
    if not passage:
        abort(404)
    return render_template("practice.html", passage=passage)


@bp.post("/api/attempts")
def save_attempt():
    data = request.get_json(silent=True) or {}
    passage_ids = {p["id"] for p in passages()}
    required = {"passage_id", "duration_seconds", "typed_characters", "correct_characters", "errors"}
    if not required.issubset(data) or data.get("passage_id") not in passage_ids:
        return jsonify(error="Invalid attempt data."), 400
    try:
        duration = float(data["duration_seconds"])
        score = calculate_score(data["typed_characters"], data["correct_characters"], data["errors"], duration)
    except (TypeError, ValueError):
        return jsonify(error="Invalid score values."), 400
    profile = selected_profile()
    now = datetime.now(UTC)
    connection = get_db()
    cursor = connection.execute(
        """INSERT INTO attempts(profile_id, passage_id, started_at, completed_at, duration_seconds,
        typed_characters, correct_characters, errors, corrected_errors, gross_wpm, net_wpm, accuracy,
        completed, error_map) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (profile["id"], data["passage_id"], (now - timedelta(seconds=duration)).isoformat(), now.isoformat(),
         duration, int(data["typed_characters"]), int(data["correct_characters"]), int(data["errors"]),
         int(data.get("corrected_errors", 0)), score["gross_wpm"], score["net_wpm"], score["accuracy"],
         int(bool(data.get("completed", True))), json.dumps(data.get("error_map", {}))),
    )
    connection.commit()
    return jsonify(id=cursor.lastrowid, **score), 201


@bp.get("/progress")
def progress():
    profile = selected_profile()
    rows = get_db().execute(
        "SELECT * FROM attempts WHERE profile_id=? ORDER BY completed_at DESC LIMIT 100", (profile["id"],)
    ).fetchall()
    best = get_db().execute(
        "SELECT COALESCE(MAX(net_wpm),0) best_wpm, COALESCE(MAX(accuracy),0) best_accuracy FROM attempts WHERE profile_id=?",
        (profile["id"],),
    ).fetchone()
    return render_template("progress.html", attempts=rows, best=best, profile=profile)


@bp.route("/parent", methods=["GET", "POST"])
def parent():
    profile = selected_profile()
    message = None
    if request.method == "POST":
        goal = request.form.get("daily_goal_minutes", type=int)
        difficulty = request.form.get("preferred_difficulty", type=int)
        if goal and 5 <= goal <= 120 and difficulty in range(1, 6):
            get_db().execute(
                "UPDATE profiles SET daily_goal_minutes=?, preferred_difficulty=? WHERE id=?",
                (goal, difficulty, profile["id"]),
            )
            get_db().commit()
            message = "Settings saved."
            profile = selected_profile()
        else:
            message = "Please use a goal from 5 to 120 minutes and a difficulty from 1 to 5."
    stats = get_db().execute(
        "SELECT COUNT(*) attempts, COALESCE(ROUND(AVG(net_wpm),1),0) wpm, COALESCE(ROUND(AVG(accuracy),1),0) accuracy FROM attempts"
    ).fetchone()
    return render_template("parent.html", profile=profile, stats=stats, message=message)


@bp.get("/export/<format_name>")
def export_data(format_name: str):
    rows = [dict(row) for row in get_db().execute("SELECT * FROM attempts ORDER BY completed_at").fetchall()]
    if format_name == "json":
        return Response(json.dumps(rows, indent=2), mimetype="application/json", headers={"Content-Disposition": "attachment; filename=scipiotyping-progress.json"})
    if format_name == "csv":
        output = io.StringIO()
        fields = list(rows[0]) if rows else ["id", "profile_id", "passage_id", "completed_at", "net_wpm", "accuracy"]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
        return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=scipiotyping-progress.csv"})
    abort(404)


@bp.get("/help")
def help_page():
    return render_template("help.html")


@bp.app_errorhandler(404)
def not_found(_error):
    return render_template("error.html", title="Page not found", message="That page is not part of the lesson map."), 404


@bp.app_errorhandler(500)
def server_error(_error):
    return render_template("error.html", title="Something went wrong", message="Your saved progress is safe. Return home and try again."), 500

