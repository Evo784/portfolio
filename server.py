"""
Portfolio Admin Server — Edwyn Houillier
Flask server with secure admin panel, project CRUD API, and image uploads.
Replaces `python -m http.server 8080` as the dev server.

Usage:
    pip install flask
    python server.py

First run generates admin credentials printed to console.
"""

import json
import os
import re
import secrets
import time
import uuid
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

# ── Paths ──────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
CONFIG_PATH = DATA_DIR / "config.json"
PROJECTS_PATH = DATA_DIR / "projects.json"

UPLOADS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg"}
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB

# ── Flask app ──────────────────────────────────────────────────

app = Flask(
    __name__,
    static_folder=None,  # We serve static files manually
    template_folder=str(BASE_DIR / "templates"),
)

app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE


# ── Config / credentials ──────────────────────────────────────

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def init_config():
    """Create admin credentials on first run."""
    config = load_config()
    if config is None:
        password = secrets.token_urlsafe(12)
        config = {
            "username": "admin",
            "password_hash": generate_password_hash(password),
            "secret_key": secrets.token_hex(32),
        }
        save_config(config)
        print("\n" + "=" * 56)
        print("  ADMIN PANEL — PREMIERS IDENTIFIANTS")
        print("=" * 56)
        print(f"  URL       : http://localhost:8080/admin/")
        print(f"  Login     : admin")
        print(f"  Password  : {password}")
        print("=" * 56)
        print("  Changez le mot de passe depuis le panneau admin.")
        print("=" * 56 + "\n")
    return config


config = init_config()
app.secret_key = config["secret_key"]


# ── Rate limiting (in-memory) ─────────────────────────────────

login_attempts = {}  # ip -> [timestamps]
RATE_LIMIT_WINDOW = 900  # 15 minutes
RATE_LIMIT_MAX = 5


def is_rate_limited(ip):
    now = time.time()
    attempts = login_attempts.get(ip, [])
    # Clean old attempts
    attempts = [t for t in attempts if now - t < RATE_LIMIT_WINDOW]
    login_attempts[ip] = attempts
    return len(attempts) >= RATE_LIMIT_MAX


def record_attempt(ip):
    now = time.time()
    if ip not in login_attempts:
        login_attempts[ip] = []
    login_attempts[ip].append(now)


# ── CSRF protection ───────────────────────────────────────────

def generate_csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]


def validate_csrf():
    token = request.headers.get("X-CSRF-Token") or request.form.get("_csrf_token")
    if not token or token != session.get("_csrf_token"):
        abort(403, "Token CSRF invalide")


# ── Auth decorator ────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Non authentifié"}), 401
            return redirect("/admin/")
        return f(*args, **kwargs)
    return decorated


# ── Project data helpers ──────────────────────────────────────

def load_projects():
    if PROJECTS_PATH.exists():
        with open(PROJECTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_projects(projects):
    with open(PROJECTS_PATH, "w", encoding="utf-8") as f:
        json.dump(projects, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[àâä]", "a", text)
    text = re.sub(r"[éèêë]", "e", text)
    text = re.sub(r"[îï]", "i", text)
    text = re.sub(r"[ôö]", "o", text)
    text = re.sub(r"[ùûü]", "u", text)
    text = re.sub(r"[ç]", "c", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "project"


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ══════════════════════════════════════════════════════════════
#  ROUTES — Static file serving
# ══════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return send_from_directory(str(BASE_DIR), "index.html")


@app.route("/styles.css")
def styles():
    return send_from_directory(str(BASE_DIR), "styles.css")


@app.route("/main.js")
def main_js():
    return send_from_directory(str(BASE_DIR), "main.js")


@app.route("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(str(BASE_DIR / "assets"), filename)


@app.route("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(str(UPLOADS_DIR), filename)


@app.route("/projects/<path:filename>")
def project_pages(filename):
    """Serve static project detail pages."""
    filepath = BASE_DIR / "projects" / filename
    if filepath.exists():
        return send_from_directory(str(BASE_DIR / "projects"), filename)
    abort(404)


# ══════════════════════════════════════════════════════════════
#  ROUTES — Dynamic project detail pages
# ══════════════════════════════════════════════════════════════

@app.route("/project/<project_id>")
def project_detail(project_id):
    """Serve dynamically generated project detail pages."""
    projects = load_projects()
    project = next((p for p in projects if p["id"] == project_id), None)
    if not project or not project.get("visible", True):
        abort(404)

    # If this project has a static page, redirect to it
    if project.get("static_page"):
        return redirect("/" + project["static_page"])

    # Find prev/next projects for navigation
    visible = sorted([p for p in projects if p.get("visible", True)], key=lambda p: p.get("order", 99))
    idx = next((i for i, p in enumerate(visible) if p["id"] == project_id), 0)
    prev_project = visible[idx - 1] if idx > 0 else None
    next_project = visible[idx + 1] if idx < len(visible) - 1 else None

    return render_template(
        "project_detail.html",
        project=project,
        prev_project=prev_project,
        next_project=next_project,
        project_num=str(idx + 1).zfill(2),
    )


# ══════════════════════════════════════════════════════════════
#  ROUTES — Admin panel
# ══════════════════════════════════════════════════════════════

@app.route("/admin/")
def admin_page():
    return send_from_directory(str(BASE_DIR / "admin"), "index.html")


@app.route("/admin/<path:filename>")
def admin_static(filename):
    return send_from_directory(str(BASE_DIR / "admin"), filename)


# ══════════════════════════════════════════════════════════════
#  API — Auth
# ══════════════════════════════════════════════════════════════

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    ip = request.remote_addr
    if is_rate_limited(ip):
        remaining = int(RATE_LIMIT_WINDOW - (time.time() - min(login_attempts.get(ip, [time.time()]))))
        return jsonify({
            "error": f"Trop de tentatives. Réessayez dans {remaining // 60} min."
        }), 429

    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    cfg = load_config()
    if username == cfg["username"] and check_password_hash(cfg["password_hash"], password):
        session["authenticated"] = True
        session["username"] = username
        generate_csrf_token()
        # Reset attempts on success
        login_attempts.pop(ip, None)
        return jsonify({
            "success": True,
            "csrf_token": session["_csrf_token"],
            "username": username,
        })

    record_attempt(ip)
    attempts_left = RATE_LIMIT_MAX - len(login_attempts.get(ip, []))
    return jsonify({
        "error": f"Identifiants incorrects. {attempts_left} tentative(s) restante(s)."
    }), 401


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/api/auth/check", methods=["GET"])
def api_auth_check():
    if session.get("authenticated"):
        return jsonify({
            "authenticated": True,
            "csrf_token": generate_csrf_token(),
            "username": session.get("username"),
        })
    return jsonify({"authenticated": False}), 401


@app.route("/api/auth/change-password", methods=["POST"])
@login_required
def api_change_password():
    validate_csrf()
    data = request.get_json(silent=True) or {}
    current = data.get("current_password", "")
    new_pw = data.get("new_password", "")

    if len(new_pw) < 8:
        return jsonify({"error": "Le mot de passe doit faire au moins 8 caractères."}), 400

    cfg = load_config()
    if not check_password_hash(cfg["password_hash"], current):
        return jsonify({"error": "Mot de passe actuel incorrect."}), 401

    cfg["password_hash"] = generate_password_hash(new_pw)
    save_config(cfg)
    return jsonify({"success": True, "message": "Mot de passe mis à jour."})


# ══════════════════════════════════════════════════════════════
#  API — Projects CRUD
# ══════════════════════════════════════════════════════════════

@app.route("/api/projects", methods=["GET"])
def api_get_projects():
    """Public endpoint — returns visible projects for the portfolio."""
    projects = load_projects()
    visible_only = request.args.get("all") != "true"
    if visible_only:
        projects = [p for p in projects if p.get("visible", True)]
    projects.sort(key=lambda p: p.get("order", 99))
    return jsonify(projects)


@app.route("/api/projects", methods=["POST"])
@login_required
def api_create_project():
    validate_csrf()
    data = request.get_json(silent=True) or {}

    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Le titre est requis."}), 400

    projects = load_projects()

    # Generate unique ID
    base_id = slugify(title)
    project_id = base_id
    counter = 1
    while any(p["id"] == project_id for p in projects):
        project_id = f"{base_id}-{counter}"
        counter += 1

    # Auto-number
    max_order = max((p.get("order", 0) for p in projects), default=0)

    project = {
        "id": project_id,
        "title": title,
        "subtitle": data.get("subtitle", ""),
        "category": data.get("category", ""),
        "tags": [t.strip() for t in data.get("tags", []) if t.strip()],
        "detail_tags": [t.strip() for t in data.get("detail_tags", []) if t.strip()],
        "description": data.get("description", ""),
        "description_2": data.get("description_2", ""),
        "overview_heading": data.get("overview_heading", ""),
        "architecture": data.get("architecture", ""),
        "architecture_highlights": [h.strip() for h in data.get("architecture_highlights", []) if h.strip()],
        "highlights_heading": data.get("highlights_heading", ""),
        "highlights_intro": data.get("highlights_intro", ""),
        "highlights": [h.strip() for h in data.get("highlights", []) if h.strip()],
        "stack": [s.strip() for s in data.get("stack", []) if s.strip()],
        "metrics": [m.strip() for m in data.get("metrics", []) if m.strip()],
        "preview_metrics": [m.strip() for m in data.get("preview_metrics", []) if m.strip()],
        "preview_url": data.get("preview_url", ""),
        "preview_type": "image",
        "github_url": data.get("github_url", ""),
        "live_url": data.get("live_url", ""),
        "youtube_url": data.get("youtube_url", ""),
        "screenshot": data.get("screenshot", ""),
        "visible": data.get("visible", True),
        "order": max_order + 1,
        "static_page": "",
        "created_at": time.strftime("%Y-%m-%d"),
    }

    projects.append(project)
    save_projects(projects)
    return jsonify(project), 201


@app.route("/api/projects/<project_id>", methods=["GET"])
def api_get_project(project_id):
    projects = load_projects()
    project = next((p for p in projects if p["id"] == project_id), None)
    if not project:
        return jsonify({"error": "Projet non trouvé."}), 404
    return jsonify(project)


@app.route("/api/projects/<project_id>", methods=["PUT"])
@login_required
def api_update_project(project_id):
    validate_csrf()
    data = request.get_json(silent=True) or {}
    projects = load_projects()
    project = next((p for p in projects if p["id"] == project_id), None)
    if not project:
        return jsonify({"error": "Projet non trouvé."}), 404

    # Update fields (keep existing values for missing fields)
    updatable = [
        "title", "subtitle", "category", "description", "description_2",
        "overview_heading", "architecture", "highlights_heading", "highlights_intro",
        "preview_url", "github_url", "live_url", "youtube_url", "screenshot",
        "visible", "order",
    ]
    for key in updatable:
        if key in data:
            project[key] = data[key]

    # Array fields
    array_fields = [
        "tags", "detail_tags", "architecture_highlights", "highlights",
        "stack", "metrics", "preview_metrics",
    ]
    for key in array_fields:
        if key in data:
            project[key] = [item.strip() for item in data[key] if isinstance(item, str) and item.strip()]

    save_projects(projects)
    return jsonify(project)


@app.route("/api/projects/<project_id>", methods=["DELETE"])
@login_required
def api_delete_project(project_id):
    validate_csrf()
    projects = load_projects()
    original_len = len(projects)
    projects = [p for p in projects if p["id"] != project_id]
    if len(projects) == original_len:
        return jsonify({"error": "Projet non trouvé."}), 404

    save_projects(projects)
    return jsonify({"success": True, "message": "Projet supprimé."})


@app.route("/api/projects/reorder", methods=["POST"])
@login_required
def api_reorder_projects():
    validate_csrf()
    data = request.get_json(silent=True) or {}
    order = data.get("order", [])  # List of project IDs in desired order

    projects = load_projects()
    id_map = {p["id"]: p for p in projects}

    for i, pid in enumerate(order):
        if pid in id_map:
            id_map[pid]["order"] = i + 1

    save_projects(projects)
    return jsonify({"success": True})


# ══════════════════════════════════════════════════════════════
#  API — Image upload
# ══════════════════════════════════════════════════════════════

@app.route("/api/upload", methods=["POST"])
@login_required
def api_upload():
    # CSRF via header (multipart forms can't easily include JSON CSRF)
    validate_csrf()

    if "file" not in request.files:
        return jsonify({"error": "Aucun fichier envoyé."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nom de fichier vide."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"Type non autorisé. Acceptés : {', '.join(ALLOWED_EXTENSIONS)}"}), 400

    # Generate unique filename
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex[:12]}.{ext}"
    filepath = UPLOADS_DIR / filename
    file.save(str(filepath))

    return jsonify({
        "success": True,
        "filename": filename,
        "path": f"uploads/{filename}",
        "url": f"/uploads/{filename}",
    })


# ══════════════════════════════════════════════════════════════
#  Run
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Portfolio server")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    print(f"\nPortfolio server running at http://localhost:{args.port}")
    print(f"Admin panel at http://localhost:{args.port}/admin/\n")
    app.run(host="0.0.0.0", port=args.port, debug=args.debug)
