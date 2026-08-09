from __future__ import annotations

import csv
import io
import json
import math
import secrets
import shutil
import sqlite3
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from flask import (Blueprint, Response, abort, current_app, flash, jsonify,
                   redirect, render_template, request, send_file, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from .content import enrich_passage, load_passages, validate_passages
from .db import SCHEMA_VERSION, get_db, init_database
from .lessons import LESSONS, lesson_passages, placement_level, progression_level, unlocked_lessons
from .progress import (ACHIEVEMENTS, KEYBOARD_ROWS, award_achievements,
                       focus_keys, key_report, recommend, streak_days, weak_keys)
from .scoring import score_text
from .targeted import targeted_passage
from .timing import daily_practice_summary, format_duration

bp = Blueprint("main", __name__)


def _custom_passages() -> list[dict]:
    rows = get_db().execute("SELECT * FROM custom_passages ORDER BY title").fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["objectives"] = json.loads(item["objectives"])
        item["vocabulary"] = json.loads(item["vocabulary"])
        items.append(enrich_passage(item, custom=True))
    return items


def passages() -> list[dict]:
    return [dict(item) for item in load_passages(current_app.config["CONTENT_PATH"])] + _custom_passages()


def practice_items() -> list[dict]:
    return passages() + lesson_passages()


def _session_targeted_passage() -> dict | None:
    item = session.get("targeted_passage")
    if not isinstance(item, dict) or not isinstance(item.get("text"), str) or not str(item.get("id", "")).startswith("targeted-"):
        return None
    return item


def _safe_error_map(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    cleaned = {}
    for key, count in list(value.items())[:50]:
        try:
            number = max(0, min(1000, int(count)))
        except (TypeError, ValueError):
            continue
        label = str(key)[:12]
        if label and number:
            cleaned[label] = number
    return cleaned


def _combined_error_map(client_value: object, final_value: object) -> dict[str, int]:
    combined = _safe_error_map(client_value)
    for key, count in _safe_error_map(final_value).items():
        combined[key] = max(combined.get(key, 0), count)
    return combined


def selected_profile():
    connection = get_db()
    profile_id = session.get("profile_id")
    profile = connection.execute("SELECT * FROM profiles WHERE id=? AND active=1", (profile_id,)).fetchone() if profile_id else None
    if profile is None:
        profile = connection.execute("SELECT * FROM profiles WHERE active=1 ORDER BY id LIMIT 1").fetchone()
        if profile: session["profile_id"] = profile["id"]
    if profile is None:
        abort(500, description="No active student profile exists.")
    return profile


@bp.app_context_processor
def daily_goal_context():
    profile = selected_profile()
    summary = daily_practice_summary(get_db(), profile["id"], profile["daily_goal_minutes"])
    return {"daily_practice": summary, "format_duration": format_duration}


def _setting(key: str, default: str = "") -> str:
    row = get_db().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def _set_setting(key: str, value: str) -> None:
    get_db().execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


def _parent_unlocked() -> bool:
    return not _setting("parent_pin_hash") or bool(session.get("parent_unlocked"))


def _require_parent() -> None:
    if not _parent_unlocked(): abort(403)


@bp.get("/health")
def health():
    get_db().execute("SELECT 1").fetchone()
    return jsonify(
        status="ok", application="ScipioTyping", schema=SCHEMA_VERSION,
        version=current_app.config["APPLICATION_VERSION"],
    )


@bp.get("/")
def index():
    profile = selected_profile()
    rows = get_db().execute("SELECT * FROM attempts WHERE profile_id=? ORDER BY completed_at DESC", (profile["id"],)).fetchall()
    stats = get_db().execute("SELECT COUNT(*) attempts, COALESCE(ROUND(AVG(adjusted_wpm),1),0) wpm, COALESCE(ROUND(AVG(accuracy),1),0) accuracy FROM attempts WHERE profile_id=?", (profile["id"],)).fetchone()
    suggestion, reason = recommend(profile, rows, passages())
    focus = focus_keys(rows)
    return render_template("index.html", profile=profile, stats=stats, passage_count=len(passages()), suggestion=suggestion, reason=reason, streak=streak_days(rows), focus=focus)


@bp.get("/library")
def library():
    category, query = request.args.get("category", ""), request.args.get("q", "").strip().lower()
    difficulty = request.args.get("difficulty", type=int)
    status = request.args.get("status", "")
    sort = request.args.get("sort", "recommended")
    if status not in {"", "not-practiced", "completed"}:
        status = ""
    if sort not in {"recommended", "recent", "title", "difficulty", "shortest", "longest"}:
        sort = "recommended"
    profile = selected_profile()
    progress_rows = get_db().execute(
        """SELECT passage_id, COUNT(*) attempt_count, MAX(adjusted_wpm) best_wpm,
                  MAX(accuracy) best_accuracy
           FROM attempts WHERE profile_id=? AND completed=1 GROUP BY passage_id""",
        (profile["id"],),
    ).fetchall()
    history = {row["passage_id"]: dict(row) for row in progress_rows}
    items = passages()
    for item in items:
        record = history.get(item["id"], {})
        item["attempt_count"] = record.get("attempt_count", 0)
        item["completed_before"] = bool(item["attempt_count"])
        item["best_wpm"] = record.get("best_wpm")
        item["best_accuracy"] = record.get("best_accuracy")
    if category: items = [p for p in items if p["category"] == category]
    if difficulty: items = [p for p in items if p["difficulty"] == difficulty]
    if query: items = [p for p in items if query in (p["title"] + " " + p["text"] + " " + p["category"]).lower()]
    if status == "not-practiced": items = [p for p in items if not p["completed_before"]]
    if status == "completed": items = [p for p in items if p["completed_before"]]

    def version_key(item):
        value = item.get("added_in", "0.0.0")
        return tuple(int(part) for part in value.split(".")) if value.count(".") == 2 and value.replace(".", "").isdigit() else (0, 0, 0)

    if sort == "title": items.sort(key=lambda item: item["title"].casefold())
    elif sort == "difficulty": items.sort(key=lambda item: (item["difficulty"], item["title"].casefold()))
    elif sort == "shortest": items.sort(key=lambda item: (item["word_count"], item["title"].casefold()))
    elif sort == "longest": items.sort(key=lambda item: (-item["word_count"], item["title"].casefold()))
    elif sort == "recent":
        items.sort(key=lambda item: item["title"].casefold())
        items.sort(key=version_key, reverse=True)
    else:
        preferred = profile["placement_level"] or profile["preferred_difficulty"] or 1
        items.sort(key=lambda item: (item["completed_before"], abs(item["difficulty"] - preferred),
                                     item["difficulty"], item["title"].casefold()))

    result_count = len(items)
    per_page = 24
    page_count = max(1, math.ceil(result_count / per_page))
    page = max(1, min(request.args.get("page", 1, type=int), page_count))
    items = items[(page - 1) * per_page:page * per_page]
    return render_template(
        "library.html", passages=items,
        categories=sorted({p["category"] for p in passages()}),
        selected_category=category, selected_difficulty=difficulty, query=query,
        selected_status=status, selected_sort=sort, page=page, page_count=page_count,
        result_count=result_count,
    )


@bp.get("/practice/<passage_id>")
def practice(passage_id: str):
    candidates = practice_items()
    targeted = _session_targeted_passage()
    if targeted:
        candidates.append(targeted)
    passage = next((item for item in candidates if item["id"] == passage_id), None)
    if not passage: abort(404)
    return render_template("practice.html", passage=passage, mode=request.args.get("mode", "practice"), lesson_id=request.args.get("lesson", ""))


@bp.get("/practice/targeted")
def targeted_practice():
    profile = selected_profile()
    rows = get_db().execute("SELECT * FROM attempts WHERE profile_id=? ORDER BY completed_at DESC", (profile["id"],)).fetchall()
    focus = focus_keys(rows)
    if not focus:
        flash("Complete more practice before starting a weak-key workshop.", "error")
        return redirect(url_for("main.progress"))
    sources = [item["text"] for item in practice_items()]
    passage = targeted_passage(profile["id"], [item["key"] for item in focus], sources)
    session["targeted_passage"] = passage
    return render_template("practice.html", passage=passage, mode="targeted", lesson_id="")


@bp.post("/api/practice-sessions")
def start_practice_session():
    data = request.get_json(silent=True) or {}
    candidates = practice_items()
    targeted = _session_targeted_passage()
    if targeted:
        candidates.append(targeted)
    passage = next((item for item in candidates if item["id"] == data.get("passage_id")), None)
    mode = data.get("mode") if data.get("mode") in {"practice", "lesson", "placement", "targeted"} else "practice"
    if not passage or (mode == "targeted" and (not targeted or passage["id"] != targeted["id"])):
        return jsonify(error="Invalid practice session."), 400
    profile = selected_profile()
    now = datetime.now(UTC).isoformat()
    identifier = secrets.token_urlsafe(18)
    connection = get_db()
    connection.execute("""INSERT INTO practice_sessions(
        id,profile_id,passage_id,mode,started_at,updated_at,active_seconds)
        VALUES(?,?,?,?,?,?,0)""", (identifier, profile["id"], passage["id"], mode, now, now))
    connection.commit()
    summary = daily_practice_summary(connection, profile["id"], profile["daily_goal_minutes"])
    return jsonify(id=identifier, daily=summary), 201


@bp.patch("/api/practice-sessions/<session_id>")
def update_practice_session(session_id: str):
    data = request.get_json(silent=True) or {}
    profile = selected_profile()
    connection = get_db()
    row = connection.execute("SELECT * FROM practice_sessions WHERE id=? AND profile_id=?", (session_id, profile["id"])).fetchone()
    try:
        active = float(data.get("active_seconds"))
    except (TypeError, ValueError):
        return jsonify(error="Invalid active time."), 400
    if not row or row["completed_at"] or active < row["active_seconds"] or active > 14400:
        return jsonify(error="Invalid practice session update."), 400
    now = datetime.now(UTC)
    started = datetime.fromisoformat(row["started_at"])
    if active > (now - started).total_seconds() + 5:
        return jsonify(error="Active time exceeds elapsed session time."), 400
    delta = active - row["active_seconds"]
    connection.execute("UPDATE practice_sessions SET active_seconds=?,updated_at=? WHERE id=?",
                       (active, now.isoformat(), session_id))
    if delta > 0:
        connection.execute("INSERT INTO practice_time_segments(session_id,recorded_at,active_seconds) VALUES(?,?,?)",
                           (session_id, now.isoformat(), delta))
    connection.commit()
    summary = daily_practice_summary(connection, profile["id"], profile["daily_goal_minutes"])
    return jsonify(session_seconds=round(active, 1), daily=summary)


@bp.post("/api/attempts")
def save_attempt():
    data = request.get_json(silent=True) or {}
    candidates = practice_items()
    targeted = _session_targeted_passage()
    if targeted:
        candidates.append(targeted)
    passage = next((p for p in candidates if p["id"] == data.get("passage_id")), None)
    try:
        duration = float(data.get("duration_seconds", 0)); typed = str(data.get("typed_text", ""))
        corrected_errors = max(0, min(10000, int(data.get("corrected_errors", 0))))
        allowance = max(20, int(len(passage["text"]) * 0.10)) if passage else 0
        if not passage or duration < 0.5 or duration > 14400 or len(typed) > len(passage["text"]) + allowance: raise ValueError
        score = score_text(passage["text"], typed, duration)
    except (TypeError, ValueError):
        return jsonify(error="Invalid attempt data."), 400
    profile = selected_profile(); now = datetime.now(UTC); connection = get_db()
    practice_session_id = data.get("practice_session_id")
    practice_session = None
    if practice_session_id:
        practice_session = connection.execute(
            "SELECT * FROM practice_sessions WHERE id=? AND profile_id=? AND passage_id=?",
            (practice_session_id, profile["id"], passage["id"]),
        ).fetchone()
        if practice_session is None or practice_session["completed_at"]:
            return jsonify(error="Invalid practice session."), 400
    mode = data.get("mode") if data.get("mode") in {"practice", "lesson", "placement", "targeted"} else "practice"
    if practice_session and practice_session["mode"] != mode:
        return jsonify(error="Practice session mode does not match."), 400
    if mode == "targeted" and (not targeted or passage["id"] != targeted["id"]):
        return jsonify(error="That targeted drill is no longer active."), 400
    lesson_id = data.get("lesson_id") if any(l["id"] == data.get("lesson_id") for l in LESSONS) else None
    focus = passage.get("focus_keys", []) if mode == "targeted" else []
    generator_version = passage.get("generator_version") if mode == "targeted" else None
    before_rows = connection.execute("SELECT * FROM attempts WHERE profile_id=? ORDER BY completed_at DESC", (profile["id"],)).fetchall()
    before_report = {item["key"]: item for item in key_report(before_rows)}
    cursor = connection.execute(
        """INSERT INTO attempts(profile_id, passage_id, started_at, completed_at, duration_seconds,
        typed_characters, correct_characters, errors, corrected_errors, gross_wpm, net_wpm, accuracy,
        completed, error_map, mode, lesson_id, adjusted_wpm, substitutions, insertions, deletions,
        transpositions, key_stats, target_text, focus_keys, generator_version, passage_revision)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (profile["id"], passage["id"], (now-timedelta(seconds=duration)).isoformat(), now.isoformat(), duration,
         score["typed_characters"], score["correct_characters"], score["errors"], corrected_errors,
         score["gross_wpm"], score["net_wpm"], score["accuracy"], int(score["completed"]),
         json.dumps(_combined_error_map(data.get("error_map"), score["error_map"])), mode, lesson_id,
         score["adjusted_wpm"], score["substitutions"], score["insertions"], score["deletions"], score["transpositions"],
         json.dumps(score["key_stats"]), passage["text"], json.dumps(focus), generator_version,
         int(passage.get("revision", passage.get("generator_version", 1)))))
    if mode == "placement" and score["completed"]:
        level = placement_level(score["net_wpm"], score["accuracy"])
        connection.execute("UPDATE profiles SET placement_level=?, placement_complete=1, preferred_difficulty=? WHERE id=?", (level, level, profile["id"]))
        score["placement_level"] = level
    if practice_session:
        final_active = max(duration, practice_session["active_seconds"])
        connection.execute("""UPDATE practice_sessions SET active_seconds=?,updated_at=?,completed_at=?,attempt_id=?
                              WHERE id=?""",
                           (final_active, now.isoformat(), now.isoformat(),
                            cursor.lastrowid, practice_session["id"]))
        if final_active > practice_session["active_seconds"]:
            connection.execute("INSERT INTO practice_time_segments(session_id,recorded_at,active_seconds) VALUES(?,?,?)",
                               (practice_session["id"], now.isoformat(), final_active-practice_session["active_seconds"]))
    else:
        implicit_id = secrets.token_urlsafe(18)
        connection.execute("""INSERT INTO practice_sessions(
            id,profile_id,passage_id,mode,started_at,updated_at,completed_at,active_seconds,attempt_id)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (implicit_id, profile["id"], passage["id"], mode,
             (now-timedelta(seconds=duration)).isoformat(), now.isoformat(), now.isoformat(), duration,
             cursor.lastrowid))
        connection.execute("INSERT INTO practice_time_segments(session_id,recorded_at,active_seconds) VALUES(?,?,?)",
                           (implicit_id, now.isoformat(), duration))
    new_awards = award_achievements(connection, profile["id"], {p["id"]:p for p in practice_items()})
    connection.commit()
    if mode == "targeted":
        session.pop("targeted_passage", None)
    after_rows = connection.execute("SELECT * FROM attempts WHERE profile_id=? ORDER BY completed_at DESC", (profile["id"],)).fetchall()
    after_report = {item["key"]: item for item in key_report(after_rows)}
    focus_feedback = []
    for key in focus:
        stats = score["key_stats"].get(key, {"expected": 0, "matched": 0, "errors": 0})
        accuracy = stats["matched"] / stats["expected"] * 100 if stats["expected"] else 0
        baseline = before_report.get(key, {}).get("recent_accuracy")
        current = after_report.get(key, {})
        recent_accuracy = current.get("recent_accuracy")
        focus_feedback.append({"key": key, "label": "Space" if key == "space" else key.upper(),
                               "accuracy": round(accuracy, 1), "baseline_accuracy": baseline,
                               "recent_accuracy": recent_accuracy, "status": current.get("status", "unknown"),
                               "change": round(recent_accuracy - baseline, 1) if baseline is not None and recent_accuracy is not None else None,
                               **stats})
    daily = daily_practice_summary(connection, profile["id"], profile["daily_goal_minutes"])
    return jsonify(id=cursor.lastrowid, corrected_errors=corrected_errors,
                   session_seconds=round(duration, 1), daily=daily,
                   achievements=[ACHIEVEMENTS[c][0] for c in new_awards], focus_feedback=focus_feedback, **score), 201


@bp.get("/lessons")
def lessons():
    profile = selected_profile(); connection = get_db()
    completed = {row[0] for row in connection.execute("SELECT DISTINCT lesson_id FROM attempts WHERE profile_id=? AND completed=1 AND lesson_id IS NOT NULL", (profile["id"],))}
    level = progression_level(profile["placement_level"] or profile["preferred_difficulty"], completed)
    drills = {p["id"].removeprefix("drill-"): p for p in lesson_passages()}
    cards = []
    for lesson in unlocked_lessons(level):
        cards.append({**lesson, "passage": drills[lesson["id"]]})
    return render_template("lessons.html", lessons=cards, profile=profile)


@bp.get("/placement")
def placement():
    candidates = [p for p in passages() if p["difficulty"] == 2]
    return render_template("placement.html", passage=candidates[0])


@bp.get("/progress")
def progress():
    profile = selected_profile(); connection = get_db()
    rows = connection.execute("SELECT * FROM attempts WHERE profile_id=? ORDER BY completed_at DESC LIMIT 100", (profile["id"],)).fetchall()
    best = connection.execute("SELECT COALESCE(MAX(adjusted_wpm),0) best_wpm, COALESCE(MAX(accuracy),0) best_accuracy, COALESCE(SUM(duration_seconds)/60,0) minutes FROM attempts WHERE profile_id=?", (profile["id"],)).fetchone()
    awards = [{"code":r["code"], "earned_at":r["earned_at"], "title":ACHIEVEMENTS.get(r["code"],(r["code"],""))[0], "description":ACHIEVEMENTS.get(r["code"],("", ""))[1]} for r in connection.execute("SELECT * FROM achievements WHERE profile_id=? ORDER BY earned_at", (profile["id"],))]
    chart = list(reversed([{"wpm":r["adjusted_wpm"],"accuracy":r["accuracy"],"date":r["completed_at"][:10]} for r in rows[:12]]))
    report = key_report(rows)
    focus = focus_keys(rows)
    return render_template("progress.html", attempts=rows, best=best, profile=profile, awards=awards, streak=streak_days(rows), weak_keys=weak_keys(rows), chart=chart, key_report=report, key_lookup={item["key"]: item for item in report}, keyboard_rows=KEYBOARD_ROWS, focus=focus)


@bp.get("/profiles")
def profiles_page():
    return render_template("profiles.html", profiles=get_db().execute("SELECT * FROM profiles WHERE active=1 ORDER BY name").fetchall(), selected=selected_profile())


@bp.post("/profiles/<int:profile_id>/select")
def select_profile(profile_id: int):
    if not get_db().execute("SELECT 1 FROM profiles WHERE id=? AND active=1", (profile_id,)).fetchone(): abort(404)
    session["profile_id"] = profile_id
    return redirect(url_for("main.index"))


@bp.route("/parent", methods=["GET", "POST"])
def parent():
    if not _parent_unlocked(): return render_template("parent_unlock.html")
    profile = selected_profile(); connection = get_db()
    if request.method == "POST":
        goal, difficulty = request.form.get("daily_goal_minutes", type=int), request.form.get("preferred_difficulty", type=int)
        if goal and 5 <= goal <= 120 and difficulty in range(1,6):
            connection.execute("UPDATE profiles SET daily_goal_minutes=?, preferred_difficulty=? WHERE id=?", (goal,difficulty,profile["id"])); connection.commit(); flash("Settings saved.", "success")
        else: flash("Use a goal from 5 to 120 minutes and difficulty from 1 to 5.", "error")
        return redirect(url_for("main.parent"))
    stats = connection.execute("SELECT COUNT(*) attempts, COALESCE(ROUND(AVG(adjusted_wpm),1),0) wpm, COALESCE(ROUND(AVG(accuracy),1),0) accuracy FROM attempts WHERE profile_id=?", (profile["id"],)).fetchone()
    return render_template("parent.html", profile=profile, stats=stats, profiles=connection.execute("SELECT * FROM profiles WHERE active=1 ORDER BY name").fetchall(), custom=_custom_passages(), pin_enabled=bool(_setting("parent_pin_hash")))


@bp.post("/parent/unlock")
def parent_unlock():
    stored = _setting("parent_pin_hash")
    if not stored or check_password_hash(stored, request.form.get("pin", "")):
        session["parent_unlocked"] = True; return redirect(url_for("main.parent"))
    flash("That PIN did not match.", "error"); return redirect(url_for("main.parent"))


@bp.post("/parent/pin")
def parent_pin():
    _require_parent(); pin = request.form.get("pin", "")
    if pin and (not pin.isdigit() or not 4 <= len(pin) <= 10): flash("PIN must contain 4–10 digits.", "error")
    else:
        _set_setting("parent_pin_hash", generate_password_hash(pin) if pin else ""); get_db().commit(); session["parent_unlocked"] = True; flash("Parent PIN updated.", "success")
    return redirect(url_for("main.parent"))


@bp.post("/parent/profiles")
def add_profile():
    _require_parent(); name = " ".join(request.form.get("name", "").split())
    if not 1 <= len(name) <= 40: flash("Profile name must contain 1–40 characters.", "error")
    else:
        try: get_db().execute("INSERT INTO profiles(name,created_at) VALUES(?,?)", (name,datetime.now(UTC).isoformat())); get_db().commit(); flash("Profile created.", "success")
        except sqlite3.IntegrityError: flash("That profile name already exists.", "error")
    return redirect(url_for("main.parent"))


@bp.post("/parent/profiles/<int:profile_id>/delete")
def delete_profile(profile_id: int):
    _require_parent(); current = selected_profile(); connection = get_db()
    target = connection.execute("SELECT * FROM profiles WHERE id=? AND active=1", (profile_id,)).fetchone()
    count = connection.execute("SELECT COUNT(*) FROM profiles WHERE active=1").fetchone()[0]
    if target is None:
        abort(404)
    if profile_id == current["id"] or count <= 1:
        flash("Switch to another profile before deleting this one.", "error")
    elif request.form.get("confirmation") != f"DELETE {target['name']}":
        flash(f"Type DELETE {target['name']} exactly.", "error")
    else:
        connection.execute("UPDATE profiles SET active=0 WHERE id=?", (profile_id,)); connection.commit(); flash("Profile removed from selection. Its records remain in the local database and backups.", "success")
    return redirect(url_for("main.parent"))


@bp.post("/parent/content")
def add_content():
    _require_parent()
    raw = request.form.to_dict(); pid = raw.get("id", "").strip().lower()
    item = {"id":pid,"title":raw.get("title","").strip(),"text":raw.get("text","").strip(),"category":raw.get("category","").strip(),"difficulty":request.form.get("difficulty",type=int),"age":request.form.get("age",type=int),"objectives":["custom practice"],"context":raw.get("context","").strip(),"vocabulary":[],"source":raw.get("source","").strip() or "Household original","rights":"original"}
    errors = validate_passages([item])
    if any(p["id"] == pid for p in passages()): errors.append("That passage ID already exists.")
    if errors: flash(" ".join(errors), "error")
    else:
        get_db().execute("INSERT INTO custom_passages VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (item["id"],item["title"],item["text"],item["category"],item["difficulty"],item["age"],json.dumps(item["objectives"]),item["context"],json.dumps(item["vocabulary"]),item["source"],item["rights"],datetime.now(UTC).isoformat())); get_db().commit(); flash("Custom passage added.", "success")
    return redirect(url_for("main.parent"))


@bp.get("/export/<format_name>")
def export_data(format_name: str):
    _require_parent()
    if format_name in {"time-json", "time-csv"}:
        rows = [dict(r) for r in get_db().execute("""SELECT practice_sessions.*, profiles.name profile_name
            FROM practice_sessions JOIN profiles ON profiles.id=practice_sessions.profile_id
            ORDER BY started_at""")]
        if format_name == "time-json":
            return Response(json.dumps(rows, indent=2), mimetype="application/json",
                            headers={"Content-Disposition":"attachment; filename=scipiotyping-practice-time.json"})
        output = io.StringIO()
        fields = list(rows[0]) if rows else ["id","profile_id","profile_name","passage_id","mode","started_at","active_seconds"]
        writer = csv.DictWriter(output, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
        return Response(output.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition":"attachment; filename=scipiotyping-practice-time.csv"})
    rows = [dict(r) for r in get_db().execute("SELECT * FROM attempts ORDER BY completed_at")]
    if format_name == "json": return Response(json.dumps(rows,indent=2),mimetype="application/json",headers={"Content-Disposition":"attachment; filename=scipiotyping-progress.json"})
    if format_name == "csv":
        output=io.StringIO(); fields=list(rows[0]) if rows else ["id","profile_id","passage_id","completed_at","net_wpm","accuracy"]; writer=csv.DictWriter(output,fieldnames=fields); writer.writeheader(); writer.writerows(rows)
        return Response(output.getvalue(),mimetype="text/csv",headers={"Content-Disposition":"attachment; filename=scipiotyping-progress.csv"})
    abort(404)


@bp.get("/parent/backup")
def backup():
    _require_parent(); temporary=tempfile.NamedTemporaryFile(suffix=".db",delete=False); temporary.close()
    destination=sqlite3.connect(temporary.name); get_db().backup(destination); destination.close()
    response = send_file(temporary.name,as_attachment=True,download_name=f"scipiotyping-backup-{datetime.now():%Y%m%d}.db")
    response.call_on_close(lambda: Path(temporary.name).unlink(missing_ok=True))
    return response


@bp.post("/parent/restore")
def restore():
    _require_parent()
    if request.form.get("confirmation") != "RESTORE" or "backup" not in request.files: flash("Type RESTORE and choose a backup file.","error"); return redirect(url_for("main.parent"))
    upload=request.files["backup"]
    temporary = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp = Path(temporary.name)
    temporary.close()
    upload.save(tmp)
    try:
        check = sqlite3.connect(tmp)
        try:
            integrity=check.execute("PRAGMA integrity_check").fetchone()[0]
            tables={r[0] for r in check.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            check.close()
        if integrity != "ok" or not {"profiles","attempts","settings"}.issubset(tables): raise ValueError
        target=Path(current_app.config["DATABASE"]); backup_dir=target.parent/"backups"; backup_dir.mkdir(exist_ok=True); shutil.copy2(target,backup_dir/f"before-restore-{datetime.now():%Y%m%d-%H%M%S}.db")
        connection=get_db(); connection.close(); from flask import g; g.pop("db",None); shutil.copy2(tmp,target); init_database(); session.pop("profile_id",None); flash("Backup restored. The previous database was preserved in instance/backups.","success")
    except (sqlite3.DatabaseError,ValueError,OSError): flash("That file is not a valid ScipioTyping backup; nothing was changed.","error")
    finally: tmp.unlink(missing_ok=True)
    return redirect(url_for("main.parent"))


@bp.post("/parent/reset")
def reset_progress():
    _require_parent(); profile=selected_profile()
    if request.form.get("confirmation") != f"RESET {profile['name']}": flash(f"Type RESET {profile['name']} exactly.","error")
    else: get_db().execute("DELETE FROM practice_sessions WHERE profile_id=?",(profile["id"],)); get_db().execute("DELETE FROM attempts WHERE profile_id=?",(profile["id"],)); get_db().execute("DELETE FROM achievements WHERE profile_id=?",(profile["id"],)); get_db().commit(); flash("Progress reset for this profile.","success")
    return redirect(url_for("main.parent"))


@bp.get("/help")
def help_page(): return render_template("help.html")


@bp.app_errorhandler(400)
def bad_request(error): return render_template("error.html",title="Request expired",message=getattr(error,"description","Return and try again.")),400
@bp.app_errorhandler(403)
def forbidden(_error): return render_template("error.html",title="Parent area locked",message="Return to Parent and enter the local PIN."),403
@bp.app_errorhandler(404)
def not_found(_error): return render_template("error.html",title="Page not found",message="That page is not part of the lesson map."),404
@bp.app_errorhandler(500)
def server_error(_error): return render_template("error.html",title="Something went wrong",message="Your saved progress is safe. Return home and try again."),500
