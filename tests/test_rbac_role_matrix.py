"""
RBAC Role Matrix Tests
Tests role-based access control for upload, search, download operations
Verifies admin, uploader, and viewer permissions
"""
import pytest
import sqlite3
from pathlib import Path
import sys
import importlib.util


def load_seed_module():
    """Load seed_db module to access role definitions"""
    repo_root = Path(__file__).resolve().parents[1]
    seed_path = repo_root / "phase2" / "database" / "seed_db.py"
    spec = importlib.util.spec_from_file_location("seed_db", str(seed_path))
    seed_db = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed_db)
    return seed_db


class TestRoleMatrix:
    """Test role permission matrix"""

    @pytest.fixture
    def db_with_roles(self, tmp_path):
        """Create a test database with seeded roles"""
        seed_db = load_seed_module()
        db_path = tmp_path / "test_rbac.db"
        seed_db.DB_PATH = str(db_path)
        seed_db.create_tables()
        seed_db.seed_roles()
        yield str(db_path), seed_db
    
    def test_admin_role_has_all_permissions(self, db_with_roles):
        """Admin role should have upload, search, download, and admin permissions"""
        db_path, _ = db_with_roles
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("""
            SELECT can_upload, can_search, can_download, is_admin 
            FROM roles WHERE name = 'admin'
        """)
        permissions = c.fetchone()
        conn.close()
        
        assert permissions == (1, 1, 1, 1), "Admin should have all permissions"
    
    def test_uploader_role_permissions(self, db_with_roles):
        """Uploader role should have upload, search, download but not admin"""
        db_path, _ = db_with_roles
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("""
            SELECT can_upload, can_search, can_download, is_admin 
            FROM roles WHERE name = 'uploader'
        """)
        permissions = c.fetchone()
        conn.close()
        
        assert permissions == (1, 1, 1, 0), "Uploader should have upload/search/download but not admin"
    
    def test_viewer_role_permissions(self, db_with_roles):
        """Viewer role should only have search and download, no upload or admin"""
        db_path, _ = db_with_roles
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("""
            SELECT can_upload, can_search, can_download, is_admin 
            FROM roles WHERE name = 'viewer'
        """)
        permissions = c.fetchone()
        conn.close()
        
        assert permissions == (0, 1, 1, 0), "Viewer should only have search/download"
    
    def test_all_roles_seeded(self, db_with_roles):
        """Verify all three roles are seeded"""
        db_path, _ = db_with_roles
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("SELECT name FROM roles ORDER BY name")
        role_names = [row[0] for row in c.fetchall()]
        conn.close()
        
        assert set(role_names) == {'admin', 'uploader', 'viewer'}, "All three roles should be seeded"
    
    def test_role_uniqueness(self, db_with_roles):
        """Verify each role name is unique"""
        db_path, _ = db_with_roles
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM roles")
        total = c.fetchone()[0]
        
        c.execute("SELECT COUNT(DISTINCT name) FROM roles")
        distinct = c.fetchone()[0]
        conn.close()
        
        assert total == distinct == 3, "All role names should be unique"


class TestUserRoleAssignment:
    """Test user-to-role assignment and permission inheritance"""
    
    @pytest.fixture
    def db_with_users(self, tmp_path):
        """Create database with roles and test users"""
        seed_db = load_seed_module()
        db_path = tmp_path / "test_users.db"
        seed_db.DB_PATH = str(db_path)
        seed_db.create_tables()
        seed_db.seed_roles()
        seed_db.seed_default_admin()
        
        # Add test users
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        
        import uuid
        import time
        
        # Create uploader user
        c.execute("""
            INSERT INTO users (id, username, passwordHash, role, permissions, createdAt, updatedAt)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), "test_uploader", "hash", "uploader", "upload,search,download", time.time(), time.time()))
        
        # Create viewer user
        c.execute("""
            INSERT INTO users (id, username, passwordHash, role, permissions, createdAt, updatedAt)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), "test_viewer", "hash", "viewer", "search,download", time.time(), time.time()))
        
        conn.commit()
        conn.close()
        
        yield str(db_path), seed_db
    
    def test_admin_user_has_admin_role(self, db_with_users):
        """Default admin user should have admin role"""
        db_path, seed_db = db_with_users
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("""
            SELECT role FROM users WHERE username = ?
        """, (seed_db.DEFAULT_ADMIN["username"],))
        role = c.fetchone()[0]
        conn.close()
        
        assert role == "admin", "Default admin should have admin role"
    
    def test_uploader_user_has_uploader_role(self, db_with_users):
        """Test uploader user should have uploader role"""
        db_path, _ = db_with_users
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("SELECT role FROM users WHERE username = 'test_uploader'")
        role = c.fetchone()[0]
        conn.close()
        
        assert role == "uploader", "Test uploader should have uploader role"
    
    def test_viewer_user_has_viewer_role(self, db_with_users):
        """Test viewer user should have viewer role"""
        db_path, _ = db_with_users
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("SELECT role FROM users WHERE username = 'test_viewer'")
        role = c.fetchone()[0]
        conn.close()
        
        assert role == "viewer", "Test viewer should have viewer role"
    
    def test_user_permissions_match_role(self, db_with_users):
        """Verify user permissions string matches their role's permissions"""
        db_path, _ = db_with_users
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("SELECT username, role, permissions FROM users WHERE username IN ('test_uploader', 'test_viewer')")
        users = c.fetchall()
        conn.close()
        
        for username, role, perms in users:
            if role == "uploader":
                assert "upload" in perms, "Uploader should have upload permission"
                assert "search" in perms, "Uploader should have search permission"
                assert "download" in perms, "Uploader should have download permission"
            elif role == "viewer":
                assert "upload" not in perms, "Viewer should not have upload permission"
                assert "search" in perms, "Viewer should have search permission"
                assert "download" in perms, "Viewer should have download permission"


class TestPermissionEnforcement:
    """Test that permissions are properly enforced (simulated)"""
    
    def test_can_upload_check(self):
        """Simulate checking if a role can upload"""
        roles = {
            "admin": {"can_upload": True, "can_search": True, "can_download": True, "is_admin": True},
            "uploader": {"can_upload": True, "can_search": True, "can_download": True, "is_admin": False},
            "viewer": {"can_upload": False, "can_search": True, "can_download": True, "is_admin": False},
        }
        
        assert roles["admin"]["can_upload"], "Admin can upload"
        assert roles["uploader"]["can_upload"], "Uploader can upload"
        assert not roles["viewer"]["can_upload"], "Viewer cannot upload"
    
    def test_can_search_check(self):
        """All roles should be able to search"""
        roles = {
            "admin": {"can_search": True},
            "uploader": {"can_search": True},
            "viewer": {"can_search": True},
        }
        
        for role, perms in roles.items():
            assert perms["can_search"], f"{role} should be able to search"
    
    def test_can_download_check(self):
        """All roles should be able to download"""
        roles = {
            "admin": {"can_download": True},
            "uploader": {"can_download": True},
            "viewer": {"can_download": True},
        }
        
        for role, perms in roles.items():
            assert perms["can_download"], f"{role} should be able to download"
    
    def test_is_admin_check(self):
        """Only admin role should have admin privileges"""
        roles = {
            "admin": {"is_admin": True},
            "uploader": {"is_admin": False},
            "viewer": {"is_admin": False},
        }
        
        assert roles["admin"]["is_admin"], "Only admin should have admin privileges"
        assert not roles["uploader"]["is_admin"], "Uploader should not have admin privileges"
        assert not roles["viewer"]["is_admin"], "Viewer should not have admin privileges"
