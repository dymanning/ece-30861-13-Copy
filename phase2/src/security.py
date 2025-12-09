import os
import re
from datetime import datetime, timezone
from typing import Any, Dict

import jwt
from fastapi import Depends, Header, HTTPException, status

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
JWT_ISSUER = os.getenv("JWT_ISSUER")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE")


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise _unauthorized("Missing Authorization header")
    match = re.match(r"^Bearer\s+(.+)$", authorization.strip(), flags=re.IGNORECASE)
    if not match:
        raise _unauthorized("Invalid Authorization header format")
    return match.group(1)


def verify_jwt_token(authorization: str = Header(None)) -> Dict[str, Any]:
    """Validate JWT signature, expiration, issuer, and audience.

    Risk: spoofed/expired tokens could bypass auth.
    Mitigation: enforce Bearer format, verify signature + exp/iss/aud, reject on failure.
    """
    token = _extract_bearer_token(authorization)
    options = {"require": ["exp", "sub"], "verify_aud": bool(JWT_AUDIENCE)}
    try:
        decoded = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE if JWT_AUDIENCE else None,
            issuer=JWT_ISSUER if JWT_ISSUER else None,
            options=options,
        )
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Token expired")
    except jwt.InvalidAudienceError:
        raise _unauthorized("Invalid token audience")
    except jwt.InvalidIssuerError:
        raise _unauthorized("Invalid token issuer")
    except jwt.PyJWTError:
        raise _unauthorized("Invalid token")

    # Extra defense: exp check in UTC
    exp = decoded.get("exp")
    if exp is not None and datetime.now(timezone.utc).timestamp() >= float(exp):
        raise _unauthorized("Token expired")
    return decoded


def get_current_user_id(claims: Dict[str, Any]) -> str | None:
    return claims.get("sub") or claims.get("user_id")


def require_role(required: str):
    def _checker(claims: Dict[str, Any] = Depends(verify_jwt_token)) -> Dict[str, Any]:
        role = claims.get("role") or claims.get("roles") or claims.get("scope")
        if isinstance(role, str):
            roles = {r.strip().lower() for r in role.split() if r.strip()}
        elif isinstance(role, (list, tuple)):
            roles = {str(r).lower() for r in role}
        else:
            roles = set()
        if required.lower() not in roles:
            raise _forbidden("Insufficient role")
        return claims

    return _checker


def require_admin(claims: Dict[str, Any] = Depends(require_role("admin"))):
    return claims
