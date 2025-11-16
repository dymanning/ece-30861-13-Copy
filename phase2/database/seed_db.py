import os
import sqlite3
import hashlib
import time

DB_PATH = os.path.join(os.path.dirname(__file__), "phase2.db")

DEFAULT_ADMIN = {
    "username": "ece30861defaultadminuser",
    "password": "correcthorsebatterystaple123(!__+@**(A;DROP TABLE packages",
    "role": "admin",
    "permissions": "upload,search,download"
}

def hash_password(password: str, salt: bytes = None) -> str:
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return salt.hex() + ":" + dk.hex()

def verify_password(password: str, stored: str) -> bool:
    salt_hex, dk_hex = stored.split(":")
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return dk.hex() == dk_hex

def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def create_tables():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            can_upload INTEGER NOT NULL DEFAULT 0,
            can_search INTEGER NOT NULL DEFAULT 1,
            can_download INTEGER NOT NULL DEFAULT 1,
            is_admin INTEGER NOT NULL DEFAULT 0
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            permissions TEXT,
            created_at REAL NOT NULL
        )
        """)
        conn.commit()

def seed_roles():
    roles = [
        ("admin", 1, 1, 1, 1),
        ("uploader", 1, 1, 1, 0),
        ("viewer", 0, 1, 1, 0)
    ]
    with get_conn() as conn:
        c = conn.cursor()
        for name, up, se, do, adm in roles:
            c.execute("""
            INSERT OR IGNORE INTO roles (name, can_upload, can_search, can_download, is_admin)
            VALUES (?, ?, ?, ?, ?)
            """, (name, up, se, do, adm))
        conn.commit()

def seed_default_admin():
    pw_hash = hash_password(DEFAULT_ADMIN["password"])
    now = time.time()
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ?", (DEFAULT_ADMIN["username"],))
        if c.fetchone():
            print("Default admin already exists.")
            return
        c.execute("""
        INSERT INTO users (username, password_hash, role, permissions, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, (
            DEFAULT_ADMIN["username"],
            pw_hash,
            DEFAULT_ADMIN["role"],
            DEFAULT_ADMIN["permissions"],
            now
        ))
        conn.commit()
        print("Seeded default admin user:", DEFAULT_ADMIN["username"])

def main():
    create_tables()
    seed_roles()
    seed_default_admin()
    print("DB initialized at:", DB_PATH)
    print("To verify, use sqlite3 or open the DB with a client.")

if __name__ == "__main__":
    main()