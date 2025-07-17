from flask import Flask, request, send_from_directory, render_template, redirect, url_for, session
import random
import json
import os
import threading
from functools import wraps

app = Flask(__name__)
app.secret_key = '4ntv9t7n4vw7nt0wntfscnjcogdanocboeaectaocnte'

UPLOAD_DIR = "user_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ADMIN_USERNAME = "dimon"
ADMIN_PASS_FILE = "admin_pass.txt"
USERS_FILE = "users.json"


def generate_admin_password():
    digits = ''.join(str(random.randint(0, 9)) for _ in range(8))
    with open(ADMIN_PASS_FILE, "w") as f:
        f.write(digits)
        f.flush()
    print("[SERVER]: Admin password saved.")
    print(f"[SERVER]: Digits: {digits}")
    print(f"[SERVER]: Admin user: {ADMIN_USERNAME}")
    return digits


def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


users = load_users()


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password_input = request.form.get("password", "").strip()

        if username == ADMIN_USERNAME:
            if not os.path.exists(ADMIN_PASS_FILE):
                return "Admin password not generated.", 500
            with open(ADMIN_PASS_FILE, "r") as f:
                admin_pass = f.read().strip()

            # Debug output
            print(f"[LOGIN DEBUG] Admin login attempt - input: '{password_input}', expected: '{admin_pass}'")

            if password_input != admin_pass:
                return render_template("invalid_password.html"), 403
            session["username"] = username
            session["role"] = "admin"
            return redirect(url_for("dashboard"))

        if username not in users:
            return render_template("invalid_password.html"), 403

        stored_pass = users[username].get("password", "").strip()
        # Debug output
        print(f"[LOGIN DEBUG] User login attempt - user: '{username}', input: '{password_input}', stored: '{stored_pass}'")
        if password_input != stored_pass:
            return render_template("invalid_password.html"), 403

        session["username"] = username
        session["role"] = users[username].get("role", "user")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            return "Username and password required.", 400

        if username in users:
            return "User already exists.", 400

        users[username] = {
            "password": password,
            "role": "user"
        }
        save_users(users)
        return redirect(url_for("login"))

    return render_template("register.html")


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            return "Error entering in admin panel: Permission denied.", 403
        return func(*args, **kwargs)

    return wrapper


@app.route("/dashboard", defaults={"subdir": ""}, methods=["GET", "POST"])
@app.route("/dashboard/<path:subdir>", methods=["GET", "POST"])
def dashboard(subdir):
    username = session.get("username")
    role = session.get("role")
    if not username:
        return redirect(url_for("login"))

    base_dir = os.path.join(UPLOAD_DIR, username)
    os.makedirs(base_dir, exist_ok=True)

    current_dir = os.path.join(base_dir, subdir)
    os.makedirs(current_dir, exist_ok=True)

    if request.method == "POST":
        folder_name = request.form.get("folder_name", "").strip()
        if folder_name:
            os.makedirs(os.path.join(current_dir, folder_name), exist_ok=True)

        file = request.files.get("file")
        if file:
            file.save(os.path.join(current_dir, file.filename))

    entries = []
    for item in os.listdir(current_dir):
        item_path = os.path.join(current_dir, item)
        is_dir = os.path.isdir(item_path)
        entries.append({
            "name": item,
            "is_dir": is_dir,
            "path": os.path.join(subdir, item).replace("\\", "/")
        })

    return render_template("dashboard.html", username=username, role=role, entries=entries, subdir=subdir)


@app.route("/admin_panel", methods=["GET", "POST"])
@admin_required
def admin_panel():
    global users
    if request.method == "POST":
        if "shutdown" in request.form:
            def shutdown_server():
                func = request.environ.get('werkzeug.server.shutdown')
                if func:
                    func()
                else:
                    print("Не удалось выключить сервер корректно.")
                threading.Timer(1.0, lambda: os._exit(0)).start()

            shutdown_server()
            return render_template("server_offing.html")

    return render_template("admin_panel.html", users=users)


@app.route("/files/<username>/<path:filename>")
def download_file(username, filename):
    return send_from_directory(os.path.join(UPLOAD_DIR, username), filename)


if __name__ == "__main__":
    generate_admin_password()
    app.run(host="0.0.0.0", port=5000)
