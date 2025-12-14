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
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    # Ensure schema is initialized
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS verifiedUsers (
                userID INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0
            )
        """)
        conn.commit()
    except Exception:
        pass  # Table may already exist
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
    token = session.get("token")
    if not token:
        return None
    
    # Handle local DB sessions (tokens starting with "db-session-")
    if token.startswith("db-session-"):
        user_data = session.get("user")
        if user_data:
            return user_data
        return None
    
    # Handle JWT tokens from external API
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

            # Check for admin role - support both local DB and external auth formats
            # Local DB users have is_admin field, external auth may have roles/role
            if role == "admin":
                has_role = user.get("is_admin", False)
                if not has_role:
                    # Also check roles/role for external auth compatibility
                    roles = user.get("roles") or user.get("role")
                    if roles:
                        if isinstance(roles, str):
                            has_role = roles == role
                        else:
                            has_role = role in roles
            else:
                # For non-admin roles, check roles/role fields
                roles = user.get("roles") or user.get("role")
                if roles is None:
                    has_role = False
                elif isinstance(roles, str):
                    has_role = roles == role
                else:
                    has_role = role in roles

            if not has_role:
                flash("You do not have permission to access that page.", "danger")
                return redirect(url_for("index"))

            return fn(*args, **kwargs)

        return wrapper

    return decorator


def ensure_default_admin_user():
    """Create/ensure default admin user exists in local DB"""
    DEFAULT_USERNAME = "ece30861defaultadminuser"
    DEFAULT_PASSWORD = "'correcthorsebatterystaple123(!__+@**(A;DROP TABLE packages'"
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if default admin already exists
        cur.execute("SELECT userID FROM verifiedUsers WHERE username = ?", (DEFAULT_USERNAME,))
        if cur.fetchone():
            conn.close()
            return
        
        # Create default admin user
        hashed = generate_password_hash(DEFAULT_PASSWORD)
        cur.execute(
            "SELECT MAX(userID) as mx FROM verifiedUsers"
        )
        row = cur.fetchone()
        next_id = (row["mx"] or 0) + 1
        
        cur.execute(
            "INSERT INTO verifiedUsers (userID, username, email, password, is_admin) VALUES (?, ?, ?, ?, ?)",
            (next_id, DEFAULT_USERNAME, f"{DEFAULT_USERNAME}@system.local", hashed, 1)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Warning: Could not ensure default admin user: {e}")


@app.route("/system/reset", methods=["POST"])
def system_reset():
    """Reset system to initial state (clears users, recreates default admin)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Clear users
        cur.execute("DELETE FROM verifiedUsers")
        conn.commit()
        conn.close()
        
        # Recreate default admin
        ensure_default_admin_user()
        
        return {"status": "ok", "message": "System reset successfully"}, 200
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500


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
                (user,)
            )
            row = cur.fetchone()
            conn.close()
            if row:
                stored = row["password"]
                # support both hashed and plaintext stored passwords
                if stored and (stored.startswith("pbkdf2:") or stored.startswith("sha256$") or stored.startswith("scrypt:")):
                    ok = check_password_hash(stored, password)
                else:
                    ok = stored == password

                if ok:
                    # store minimal session info; keep the token key for compatibility
                    session["token"] = "db-session-" + str(row["userID"])
                    session["user"] = {"userID": row["userID"], "email": row["email"], "username": row["username"], "is_admin": bool(row["is_admin"])}
                    flash("Logged in successfully (local DB).", "success")
                    next_url = request.args.get("next") or url_for("dashboard")
                    return redirect(next_url)
                else:
                    # Password mismatch
                    flash("Invalid username or password.", "danger")
            else:
                # no local user found
                flash("Invalid username or password.", "danger")
        except sqlite3.Error as e:
            # Server-side database error
            flash("A server error occurred. Please try again later.", "danger")
            app.logger.error(f"Database error during login: {e}")
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
    
    # Fetch all users for admin panel
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT userID, username, email, is_admin FROM verifiedUsers ORDER BY username")
        users = [dict(row) for row in cur.fetchall()]
        conn.close()
    except sqlite3.Error as e:
        app.logger.error(f"Error fetching users: {e}")
        users = []
    
    return render_template("admin.html", user=user, users=users)


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
    # Ensure default admin user exists on startup
    ensure_default_admin_user()
    # For local development only. Use a real WSGI server in production.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)), debug=True)
