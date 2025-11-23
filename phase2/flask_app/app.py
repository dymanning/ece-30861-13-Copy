import os
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret")

# External JWT API base URL (expected to expose /auth/login and /auth/register and a verify endpoint)
JWT_API_URL = os.environ.get("JWT_API_URL", "http://localhost:5001")
# Endpoint path used to verify token / fetch current user (default: /auth/me)
JWT_VERIFY_PATH = os.environ.get("JWT_VERIFY_PATH", "/auth/me")


def api_url(path: str) -> str:
    return JWT_API_URL.rstrip("/") + path


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


@app.route("/")
def index():
    return render_template("index.html", logged_in=("token" in session))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        try:
            resp = requests.post(api_url("/auth/login"), json={"email": email, "password": password}, timeout=5)
        except requests.RequestException:
            flash("Unable to reach auth server.", "danger")
            return render_template("login.html")

        if resp.status_code == 200:
            data = resp.json()
            token = data.get("access_token") or data.get("token")
            if token:
                session["token"] = token
                flash("Logged in successfully.", "success")
                next_url = request.args.get("next") or url_for("dashboard")
                return redirect(next_url)
        # otherwise
        flash("Login failed. Check credentials.", "danger")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        try:
            resp = requests.post(api_url("/auth/register"), json={"email": email, "password": password}, timeout=5)
        except requests.RequestException:
            flash("Unable to reach auth server.", "danger")
            return render_template("register.html")

        if resp.status_code in (200, 201):
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))
        flash("Registration failed. See server response.", "danger")
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


if __name__ == "__main__":
    # For local development only. Use a real WSGI server in production.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)), debug=True)
