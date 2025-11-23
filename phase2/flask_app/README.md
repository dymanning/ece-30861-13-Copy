# Flask front-end scaffold for JWT-backed auth

This folder contains a minimal Flask front-end that talks to an external JWT API.

Files added:
- `app.py` - main Flask application (already present) with server-side flow: forms POST to Flask, Flask calls JWT API and stores token in session cookie.
- `templates/` - `base.html`, `index.html`, `login.html`, `register.html`, `dashboard.html`.
- `static/style.css` - small stylesheet.
- `requirements.txt` - dependencies.

Environment variables:
- `FLASK_SECRET` - secret for Flask sessions (default: `dev-secret` in development).
- `JWT_API_URL` - base URL of your JWT auth API (default: `http://localhost:5001`).
- `JWT_VERIFY_PATH` - path for verifying token (default: `/auth/me`).

How it works (server-side flow):
1. User submits the login form to `/login`.
2. Flask forwards credentials to `POST {JWT_API_URL}/auth/login`.
3. On success, Flask stores the returned token in the server-side session (cookie) and redirects to the dashboard.
4. Protected endpoints call the configured verify endpoint (`JWT_VERIFY_PATH`) with the token to obtain user info.

Run locally (development):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=app.py
export FLASK_SECRET="replace-with-secret"
export JWT_API_URL=http://localhost:5001
flask run --host=0.0.0.0 --port=3000
```

Notes:
- This template expects an external auth API exposing typical endpoints under `/auth` like `/auth/login`, `/auth/register`, and a verification endpoint such as `/auth/me` that returns the current user for a valid bearer token.
- For production, run behind a WSGI server and set secure session cookie settings.
