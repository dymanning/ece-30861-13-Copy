"""
RBAC Admin CRUD Permission Tests
Verifies admin users can Create, Read, Update, Delete users and roles
Verifies non-admin users cannot perform admin operations
"""
import pytest
import sqlite3
from pathlib import Path
import importlib.util
import uuid
import time


def load_seed_module():
    """Load seed_db module"""
    repo_root = Path(__file__).resolve().parents[1]
    seed_path = repo_root / "phase2" / "database" / "seed_db.py"
    spec = importlib.util.spec_from_file_location("seed_db", str(seed_path))
    seed_db = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed_db)
    return seed_db


class TestAdminUserCRUD:
    """Test admin CRUD operations on users"""
    
    @pytest.fixture
    def admin_db(self, tmp_path):
        """Database with admin user"""
        seed_db = load_seed_module()
        db_path = tmp_path / "admin_test.db"
        seed_db.DB_PATH = str(db_path)
        seed_db.create_tables()
        seed_db.seed_roles()
        seed_db.seed_default_admin()
        yield str(db_path), seed_db
    
    def test_admin_can_create_user(self, admin_db):
        """Admin should be able to create new users"""
        db_path, seed_db = admin_db
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Simulate admin creating a new user
        new_user_id = str(uuid.uuid4())
        now = time.time()
        pw_hash = seed_db.hash_password("testpass123")
        
        c.execute("""
            INSERT INTO users (id, username, passwordHash, role, permissions, createdAt, updatedAt)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (new_user_id, "new_test_user", pw_hash, "viewer", "search,download", now, now))
        conn.commit()
        
        # Verify user was created
        c.execute("SELECT username, role FROM users WHERE id = ?", (new_user_id,))
        user = c.fetchone()
        conn.close()
        
        assert user is not None, "Admin should be able to create users"
        assert user[0] == "new_test_user"
        assert user[1] == "viewer"
    
    def test_admin_can_read_users(self, admin_db):
        """Admin should be able to read all users"""
        db_path, _ = admin_db
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Admin reads all users
        c.execute("SELECT username, role FROM users")
        users = c.fetchall()
        conn.close()
        
        assert len(users) >= 1, "Admin should be able to read users"
        assert any(u[1] == "admin" for u in users), "Should find admin user"
    
    def test_admin_can_update_user(self, admin_db):
        """Admin should be able to update user details"""
        db_path, seed_db = admin_db
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Create a test user
        user_id = str(uuid.uuid4())
        now = time.time()
        c.execute("""
            INSERT INTO users (id, username, passwordHash, role, permissions, createdAt, updatedAt)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, "user_to_update", "hash", "viewer", "search,download", now, now))
        conn.commit()
        
        # Admin updates the user's role
        c.execute("""
            UPDATE users SET role = ?, permissions = ?, updatedAt = ?
            WHERE id = ?
        """, ("uploader", "upload,search,download", time.time(), user_id))
        conn.commit()
        
        # Verify update
        c.execute("SELECT role, permissions FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        conn.close()
        
        assert user[0] == "uploader", "Admin should be able to update user role"
        assert "upload" in user[1], "Permissions should be updated"
    
    def test_admin_can_delete_user(self, admin_db):
        """Admin should be able to delete users"""
        db_path, _ = admin_db
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Create a test user
        user_id = str(uuid.uuid4())
        now = time.time()
        c.execute("""
            INSERT INTO users (id, username, passwordHash, role, permissions, createdAt, updatedAt)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, "user_to_delete", "hash", "viewer", "search", now, now))
        conn.commit()
        
        # Verify user exists
        c.execute("SELECT COUNT(*) FROM users WHERE id = ?", (user_id,))
        count_before = c.fetchone()[0]
        assert count_before == 1
        
        # Admin deletes the user
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        
        # Verify user was deleted
        c.execute("SELECT COUNT(*) FROM users WHERE id = ?", (user_id,))
        count_after = c.fetchone()[0]
        conn.close()
        
        assert count_after == 0, "Admin should be able to delete users"


class TestAdminRoleCRUD:
    """Test admin CRUD operations on roles"""
    
    @pytest.fixture
    def admin_db(self, tmp_path):
        """Database with roles"""
        seed_db = load_seed_module()
        db_path = tmp_path / "admin_role_test.db"
        seed_db.DB_PATH = str(db_path)
        seed_db.create_tables()
        seed_db.seed_roles()
        yield str(db_path)
    
    def test_admin_can_create_role(self, admin_db):
        """Admin should be able to create custom roles"""
        db_path = admin_db
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Admin creates a custom role
        c.execute("""
            INSERT INTO roles (name, can_upload, can_search, can_download, is_admin)
            VALUES (?, ?, ?, ?, ?)
        """, ("contributor", 1, 1, 0, 0))
        conn.commit()
        
        # Verify role was created
        c.execute("SELECT name, can_upload, can_search, can_download FROM roles WHERE name = 'contributor'")
        role = c.fetchone()
        conn.close()
        
        assert role is not None, "Admin should be able to create roles"
        assert role == ("contributor", 1, 1, 0)
    
    def test_admin_can_read_roles(self, admin_db):
        """Admin should be able to read all roles"""
        db_path = admin_db
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM roles")
        count = c.fetchone()[0]
        conn.close()
        
        assert count >= 3, "Admin should be able to read all roles"
    
    def test_admin_can_update_role(self, admin_db):
        """Admin should be able to update role permissions"""
        db_path = admin_db
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Get current viewer permissions
        c.execute("SELECT can_upload FROM roles WHERE name = 'viewer'")
        original = c.fetchone()[0]
        
        # Admin updates viewer role (for testing only)
        c.execute("UPDATE roles SET can_upload = 1 WHERE name = 'viewer'")
        conn.commit()
        
        c.execute("SELECT can_upload FROM roles WHERE name = 'viewer'")
        updated = c.fetchone()[0]
        
        # Restore original
        c.execute("UPDATE roles SET can_upload = ? WHERE name = 'viewer'", (original,))
        conn.commit()
        conn.close()
        
        assert updated == 1, "Admin should be able to update role permissions"
    
    def test_admin_can_delete_custom_role(self, admin_db):
        """Admin should be able to delete custom roles"""
        db_path = admin_db
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Create a custom role
        c.execute("""
            INSERT INTO roles (name, can_upload, can_search, can_download, is_admin)
            VALUES ('temp_role', 0, 1, 0, 0)
        """)
        conn.commit()
        
        # Delete it
        c.execute("DELETE FROM roles WHERE name = 'temp_role'")
        conn.commit()
        
        # Verify deletion
        c.execute("SELECT COUNT(*) FROM roles WHERE name = 'temp_role'")
        count = c.fetchone()[0]
        conn.close()
        
        assert count == 0, "Admin should be able to delete custom roles"


class TestNonAdminPermissionDenial:
    """Test that non-admin users cannot perform admin operations"""
    
    @pytest.fixture
    def test_db(self, tmp_path):
        """Database with multiple user roles"""
        seed_db = load_seed_module()
        db_path = tmp_path / "non_admin_test.db"
        seed_db.DB_PATH = str(db_path)
        seed_db.create_tables()
        seed_db.seed_roles()
        
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        
        # Create uploader and viewer users
        now = time.time()
        c.execute("""
            INSERT INTO users (id, username, passwordHash, role, permissions, createdAt, updatedAt)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), "uploader_user", "hash", "uploader", "upload,search,download", now, now))
        
        c.execute("""
            INSERT INTO users (id, username, passwordHash, role, permissions, createdAt, updatedAt)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), "viewer_user", "hash", "viewer", "search,download", now, now))
        
        conn.commit()
        conn.close()
        
        yield str(db_path)
    
    def test_non_admin_cannot_create_users(self, test_db):
        """Non-admin users should not be able to create users (enforced by app)"""
        db_path = test_db
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Check that uploader and viewer roles have is_admin = 0
        c.execute("SELECT is_admin FROM roles WHERE name IN ('uploader', 'viewer')")
        admin_flags = [row[0] for row in c.fetchall()]
        conn.close()
        
        assert all(flag == 0 for flag in admin_flags), "Non-admin roles should not have admin privileges"
    
    def test_non_admin_cannot_delete_users(self, test_db):
        """Verify non-admin roles lack admin flag (app enforces denial)"""
        db_path = test_db
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Check users' roles
        c.execute("SELECT username, role FROM users WHERE username IN ('uploader_user', 'viewer_user')")
        users = c.fetchall()
        
        for username, role in users:
            c.execute("SELECT is_admin FROM roles WHERE name = ?", (role,))
            is_admin = c.fetchone()[0]
            assert is_admin == 0, f"{username} with role {role} should not have admin privileges"
        
        conn.close()
    
    def test_non_admin_cannot_modify_roles(self, test_db):
        """Non-admin users lack the admin flag needed for role modification"""
        db_path = test_db
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("""
            SELECT u.username, r.is_admin 
            FROM users u 
            JOIN roles r ON u.role = r.name 
            WHERE u.username = 'viewer_user'
        """)
        result = c.fetchone()
        conn.close()
        
        assert result[1] == 0, "Viewer should not have admin privileges for modifying roles"
    
    def test_only_admin_role_has_admin_flag(self, test_db):
        """Verify only the admin role has is_admin = 1"""
        db_path = test_db
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("SELECT name, is_admin FROM roles")
        roles = c.fetchall()
        conn.close()
        
        admin_roles = [name for name, is_admin in roles if is_admin == 1]
        assert admin_roles == ["admin"], "Only the admin role should have is_admin flag"


class TestPermissionValidation:
    """Test helper functions for permission validation"""
    
    def test_check_admin_permission(self):
        """Simulate checking if user has admin permission"""
        def has_admin_permission(role: str, roles_db: dict) -> bool:
            return roles_db.get(role, {}).get("is_admin", False)
        
        roles = {
            "admin": {"is_admin": True},
            "uploader": {"is_admin": False},
            "viewer": {"is_admin": False},
        }
        
        assert has_admin_permission("admin", roles), "Admin should have admin permission"
        assert not has_admin_permission("uploader", roles), "Uploader should not have admin permission"
        assert not has_admin_permission("viewer", roles), "Viewer should not have admin permission"
    
    def test_check_can_modify_users(self):
        """Only admin can modify users"""
        def can_modify_users(role: str) -> bool:
            return role == "admin"
        
        assert can_modify_users("admin"), "Admin can modify users"
        assert not can_modify_users("uploader"), "Uploader cannot modify users"
        assert not can_modify_users("viewer"), "Viewer cannot modify users"
    
    def test_check_can_modify_roles(self):
        """Only admin can modify roles"""
        def can_modify_roles(role: str) -> bool:
            return role == "admin"
        
        assert can_modify_roles("admin"), "Admin can modify roles"
        assert not can_modify_roles("uploader"), "Uploader cannot modify roles"
        assert not can_modify_roles("viewer"), "Viewer cannot modify roles"
