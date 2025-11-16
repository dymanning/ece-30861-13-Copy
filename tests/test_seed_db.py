import sqlite3
import importlib.util
import pathlib

def load_seed_module():
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    seed_path = repo_root / "phase2" / "database" / "seed_db.py"
    spec = importlib.util.spec_from_file_location("seed_db", str(seed_path))
    seed_db = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed_db)
    return seed_db

def test_seed_roles_and_default_admin(tmp_path):
    seed_db = load_seed_module()
    seed_db.DB_PATH = str(tmp_path / "phase2.db")

    # run the seeding logic
    seed_db.main()

    # verify DB contents
    conn = sqlite3.connect(seed_db.DB_PATH)
    c = conn.cursor()

    c.execute("SELECT name, can_upload, can_search, can_download, is_admin FROM roles")
    roles = {row[0]: row[1:] for row in c.fetchall()}
    assert "admin" in roles, "admin role missing"
    assert roles["admin"][-1] == 1, "admin role not marked as admin"

    c.execute("SELECT username, role, password_hash FROM users WHERE username = ?", (seed_db.DEFAULT_ADMIN["username"],))
    user = c.fetchone()
    assert user is not None, "default admin user missing"
    assert user[1] == "admin", "default admin has wrong role"

    # optional: verify password verification if implemented
    if hasattr(seed_db, "verify_password"):
        assert seed_db.verify_password(seed_db.DEFAULT_ADMIN["password"], user[2]), "password verification failed"

    conn.close()

def test_idempotent_seeding(tmp_path):
    seed_db = load_seed_module()
    seed_db.DB_PATH = str(tmp_path / "phase2.db")

    # Run seeding twice
    seed_db.main()
    seed_db.main()

    conn = sqlite3.connect(seed_db.DB_PATH)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users WHERE username = ?", (seed_db.DEFAULT_ADMIN["username"],))
    user_count = c.fetchone()[0]
    assert user_count == 1, "default admin was inserted more than once"

    c.execute("SELECT COUNT(*) FROM roles WHERE name = 'admin'")
    role_count = c.fetchone()[0]
    assert role_count == 1, "admin role was inserted more than once"

    conn.close()

def test_role_permissions_values(tmp_path):
    seed_db = load_seed_module()
    seed_db.DB_PATH = str(tmp_path / "phase2.db")
    seed_db.main()

    conn = sqlite3.connect(seed_db.DB_PATH)
    c = conn.cursor()

    c.execute("SELECT name, can_upload, can_search, can_download, is_admin FROM roles")
    roles = {row[0]: row[1:] for row in c.fetchall()}

    assert roles["admin"] == (1, 1, 1, 1)
    assert roles["uploader"] == (1, 1, 1, 0)
    assert roles["viewer"] == (0, 1, 1, 0)

    conn.close()

def test_password_hashing_and_verification(tmp_path):
    seed_db = load_seed_module()
    seed_db.DB_PATH = str(tmp_path / "phase2.db")
    seed_db.main()

    conn = sqlite3.connect(seed_db.DB_PATH)
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username = ?", (seed_db.DEFAULT_ADMIN["username"],))
    row = c.fetchone()
    assert row is not None
    pw_hash = row[0]

    # Not stored in plaintext and uses the expected "salt:hash" format
    assert pw_hash != seed_db.DEFAULT_ADMIN["password"]
    assert ":" in pw_hash

    # verify_password should accept correct and reject incorrect passwords (if implemented)
    if hasattr(seed_db, "verify_password"):
        assert seed_db.verify_password(seed_db.DEFAULT_ADMIN["password"], pw_hash)
        assert not seed_db.verify_password("wrongpassword", pw_hash)

    conn.close()