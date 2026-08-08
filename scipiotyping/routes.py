from __future__ import annotations

import csv
import io
import json
import shutil
import sqlite3
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from flask import (Blueprint, Response, abort, current_app, flash, jsonify,
                   redirect, render_template, request, send_file, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from .content import load_passages, validate_passages
from .db import get_db, init_database
from .lessons import LESSONS, lesson_passages, placement_level, progression_level, unlocked_lessons
from .progress import ACHIEVEMENTS, award_achievements, recommend, streak_days, weak_keys
from .scoring import score_text

bp = Blueprint("main", __name__)


def _custom_passages() -> list[dict]:
    rows = get_db().execute("SELECT * FROM custom_passages ORDER BY title").fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["objectives"] = json.loads(item["objectives"])
        item["vocabulary"] = json.loads(item["vocabulary"])
        items.append(item)
    return items


def passages() -> list[dict]:
    items = [dict(item) for item in load_passages(current_app.config["CONTENT_PATH"])] + _custom_passages()
    for item in items:
        item["word_count"] = len(item["text"].split())
        item["character_count"] = len(item["text"])
    return items


def practice_items() -> list[dict]:
    return passages() + lesson_passages()


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
    return jsonify(status="ok", application="ScipioTyping", schema=4)


@bp.get("/")
def index():
    profile = selected_profile()
    rows = get_db().execute("SELECT * FROM attempts WHERE profile_id=? ORDER BY completed_at DESC", (profile["id"],)).fetchall()
    stats = get_db().execute("SELECT COUNT(*) attempts, COALESCE(ROUND(AVG(adjusted_wpm),1),0) wpm, COALESCE(ROUND(AVG(accuracy),1),0) accuracy FROM attempts WHERE profile_id=?", (profile["id"],)).fetchone()
    suggestion, reason = recommend(profile, rows, passages())
    return render_template("index.html", profile=profile, stats=stats, passage_count=len(passages()), suggestion=suggestion, reason=reason, streak=streak_days(rows))


@bp.get("/library")
def library():
    category, query = request.args.get("category", ""), request.args.get("q", "").strip().lower()
    difficulty = request.args.get("difficulty", type=int)
    items = passages()
    if category: items = [p for p in items if p["category"] == category]
    if difficulty: items = [p for p in items if p["difficulty"] == difficulty]
    if query: items = [p for p in items if query in (p["title"] + " " + p["text"] + " " + p["category"]).lower()]
    return render_template("library.html", passages=items, categories=sorted({p["category"] for p in passages()}), selected_category=category, selected_difficulty=difficulty, query=query)


@bp.get("/practice/<passage_id>")
def practice(passage_id: str):
    passage = next((item for item in practice_items() if item["id"] == passage_id), None)
    if not passage: abort(404)
    return render_template("practice.html", passage=passage, mode=request.args.get("mode", "practice"), lesson_id=request.args.get("lesson", ""))


@bp.post("/api/attempts")
def save_attempt():
    data = request.get_json(silent=True) or {}
    passage = next((p for p in practice_items() if p["id"] == data.get("passage_id")), None)
    try:
        duration = float(data.get("duration_seconds", 0)); typed = str(data.get("typed_text", ""))
        corrected_errors = max(0, min(10000, int(data.get("corrected_errors", 0))))
        allowance = max(20, int(len(passage["text"]) * 0.10)) if passage else 0
        if not passage or duration < 0.5 or duration > 14400 or len(typed) > len(passage["text"]) + allowance: raise ValueError
        score = score_text(passage["text"], typed, duration)
    except (TypeError, ValueError):
        return jsonify(error="Invalid attempt data."), 400
    profile = selected_profile(); now = datetime.now(UTC); connection = get_db()
    mode = data.get("mode") if data.get("mode") in {"practice", "lesson", "placement"} else "practice"
    lesson_id = data.get("lesson_id") if any(l["id"] == data.get("lesson_id") for l in LESSONS) else None
    cursor = connection.execute(
        """INSERT INTO attempts(profile_id, passage_id, started_at, completed_at, duration_seconds,
        typed_characters, correct_characters, errors, corrected_errors, gross_wpm, net_wpm, accuracy,
        completed, error_map, mode, lesson_id, adjusted_wpm, substitutions, insertions, deletions,
        transpositions) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (profile["id"], passage["id"], (now-timedelta(seconds=duration)).isoformat(), now.isoformat(), duration,
         score["typed_characters"], score["correct_characters"], score["errors"], corrected_errors,
         score["gross_wpm"], score["net_wpm"], score["accuracy"], int(score["completed"]),
         json.dumps(_combined_error_map(data.get("error_map"), score["error_map"])), mode, lesson_id,
         score["adjusted_wpm"], score["substitutions"], score["insertions"], score["deletions"], score["transpositions"]))
    if mode == "placement" and score["completed"]:
        level = placement_level(score["net_wpm"], score["accuracy"])
        connection.execute("UPDATE profiles SET placement_level=?, placement_complete=1, preferred_difficulty=? WHERE id=?", (level, level, profile["id"]))
        score["placement_level"] = level
    new_awards = award_achievements(connection, profile["id"], {p["id"]:p for p in practice_items()})
    connection.commit()
    return jsonify(id=cursor.lastrowid, corrected_errors=corrected_errors,
                   achievements=[ACHIEVEMENTS[c][0] for c in new_awards], **score), 201


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
    return render_template("progress.html", attempts=rows, best=best, profile=profile, awards=awards, streak=streak_days(rows), weak_keys=weak_keys(rows), chart=chart)


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
    _require_parent(); rows = [dict(r) for r in get_db().execute("SELECT * FROM attempts ORDER BY completed_at")]
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
    else: get_db().execute("DELETE FROM attempts WHERE profile_id=?",(profile["id"],)); get_db().execute("DELETE FROM achievements WHERE profile_id=?",(profile["id"],)); get_db().commit(); flash("Progress reset for this profile.","success")
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
