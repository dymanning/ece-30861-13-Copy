"""Wrapper that loads security helpers from ../security-scripts/security.py."""

from importlib import util
from pathlib import Path
from typing import Any, Dict

_IMPL_PATH = Path(__file__).resolve().parents[1] / "security-scripts" / "security.py"
_SPEC = util.spec_from_file_location("security_scripts_impl", _IMPL_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Cannot load security module from {_IMPL_PATH}")
_MODULE = util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

# Re-export public helpers
verify_jwt_token = _MODULE.verify_jwt_token
require_role = _MODULE.require_role
require_admin = _MODULE.require_admin
get_current_user_id = _MODULE.get_current_user_id

__all__ = [
    "verify_jwt_token",
    "require_role",
    "require_admin",
    "get_current_user_id",
]
