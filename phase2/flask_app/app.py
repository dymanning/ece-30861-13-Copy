import os
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret")

# Recommended production cookie settings (can be overridden via env)
app.config.update(
    SESSION_COOKIE_HTTPONLY=os.environ.get("SESSION_COOKIE_HTTPONLY", "True") == "True",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "False") == "True",
    SESSION_COOKIE_SAMESITE=os.environ.get("SESSION_COOKIE_SAMESITE", "Lax"),
)

# External JWT API base URL (expected to expose /auth/login and /auth/register and a verify endpoint)
JWT_API_URL = os.environ.get("JWT_API_URL", "http://localhost:5001")
# Endpoint path used to verify token / fetch current user (default: /auth/me)
JWT_VERIFY_PATH = os.environ.get("JWT_VERIFY_PATH", "/auth/me")


def api_url(path: str) -> str:
    return JWT_API_URL.rstrip("/") + path


def get_db_path() -> str:
    # database located at phase2/flask_app/data/allUsers.db
    return os.path.join(app.root_path, "data", "allUsers.db")


def get_db_connection():
    path = get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def get_auth_headers():
    token = session.get("token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def verify_token() -> dict | None:
    """Attempt to verify token by calling the configured verify endpoint.
    Returns user JSON on success, None on failure.
    """
    headers = get_auth_headers()
    if not headers:
        return None
    try:
        resp = requests.get(api_url(JWT_VERIFY_PATH), headers=headers, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except requests.RequestException:
        pass
    return None


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = verify_token()
        if not user:
            flash("Please sign in to access that page.", "warning")
            return redirect(url_for("login", next=request.path))
        # attach user to request context via flask.g if needed
        return fn(*args, **kwargs)

    return wrapper


def role_required(role: str):
    """Decorator to restrict access to users that have a given role in their user info.
    The external auth verify endpoint is expected to return a JSON object with a `roles`
    list or a `role` string. If verification fails or role is missing, redirect to login.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = verify_token()
            if not user:
                flash("Please sign in to access that page.", "warning")
                return redirect(url_for("login", next=request.path))

            # roles may be a list or a single string
            roles = user.get("roles") or user.get("role")
            if roles is None:
                flash("You do not have permission to access that page.", "danger")
                return redirect(url_for("index"))

            if isinstance(roles, str):
                has_role = roles == role
            else:
                has_role = role in roles

            if not has_role:
                flash("You do not have permission to access that page.", "danger")
                return redirect(url_for("index"))

            return fn(*args, **kwargs)

        return wrapper

    return decorator


@app.route("/")
def index():
    return render_template("index.html", logged_in=("token" in session))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username")
        password = request.form.get("password")
        # Try local SQLite authentication first
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            # match by email or username
            cur.execute(
                "SELECT * FROM verifiedUsers WHERE username = ?",
                (user)
            )
            row = cur.fetchone()
            conn.close()
            if row:
                stored = row["password"]
                # support both hashed and plaintext stored passwords
                if stored and (stored.startswith("pbkdf2:") or stored.startswith("sha256$")):
                    ok = check_password_hash(stored, password)
                else:
                    ok = stored == password

                if ok:
                    # store minimal session info; keep the token key for compatibility
                    session["token"] = "db-session-" + str(row["userID"])
                    session["user"] = {"userID": row["userID"], "email": row["email"], "username": row["username"]}
                    flash("Logged in successfully (local DB).", "success")
                    next_url = request.args.get("next") or url_for("dashboard")
                    return redirect(next_url)
                else:
                    flash("Login failed. Check credentials.", "danger")
            else:
                # no local user found
                flash("Login failed. Check credentials.", "danger")
        except sqlite3.Error:
            flash("Unable to reach auth server.", "danger")
            return render_template("login.html")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        username = request.form.get("username")
        # Create user in local SQLite DB
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            # check for existing email or username
            cur.execute("SELECT userID FROM verifiedUsers WHERE email = ? OR username = ?", (email, username))
            if cur.fetchone():
                flash("A user with that email or username already exists.", "warning")
                conn.close()
                return render_template("register.html")

            # compute next userID
            cur.execute("SELECT MAX(userID) as mx FROM verifiedUsers")
            row = cur.fetchone()
            next_id = (row["mx"] or 0) + 1

            hashed = generate_password_hash(password)
            cur.execute(
                "INSERT INTO verifiedUsers (userID, email, username, password) VALUES (?, ?, ?, ?)",
                (next_id, email, username, hashed),
            )
            conn.commit()
            conn.close()
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.Error as e:
            flash("Unable to reach auth server.", "danger")
            return render_template("register.html")
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.pop("token", None)
    flash("Logged out.", "info")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = verify_token()
    return render_template("dashboard.html", user=user)


@app.route("/admin")
@role_required("admin")
def admin():
    user = verify_token()
    return render_template("dashboard.html", user=user)


@app.errorhandler(404)
def not_found(err):
    return render_template("error.html", title="Not Found", message="The requested page was not found."), 404


@app.errorhandler(500)
def server_error(err):
    return render_template(
        "error.html",
        title="Server Error",
        message=(str(err) or "An internal server error occurred."),
    ), 500


if __name__ == "__main__":
    # For local development only. Use a real WSGI server in production.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)), debug=True)
