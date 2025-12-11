# Security Implementation Summary

## Overview
This document outlines the security hardening measures implemented in the ECE 461 Artifact Registry API following STRIDE threat modeling recommendations.

## Security Measures Implemented

### 1. Authentication & Authorization

**JWT Token Verification**
- All sensitive endpoints require JWT token via `X-Authorization` header
- Server-side signature verification using HS256 algorithm
- Token expiration validation (configurable via `JWT_EXPIRATION_HOURS`)
- Issuer and audience validation
- Malformed/invalid tokens rejected with HTTP 401

**RBAC (Role-Based Access Control)**
- Admin-only endpoints (`/reset`, `/artifacts/{type}/{id}` DELETE) require `role: "admin"` claim
- Non-admin users rejected with HTTP 403
- Role claim extracted and validated from token

**Environment Configuration**
- `JWT_SECRET`: Token signing secret (from environment)
- `JWT_ISSUER`: Expected token issuer (default: "ece-461-registry")
- `JWT_AUDIENCE`: Expected token audience (default: "ece-461-api")
- `JWT_EXPIRATION_HOURS`: Token lifetime (default: 24 hours)

### 2. Protected Endpoints

| Endpoint | Method | Auth Required | RBAC Role | Action Logged |
|----------|--------|--------------|-----------|--------------|
| `/reset` | DELETE | ✓ JWT | admin | Yes |
| `/artifact/{type}` | POST | ✓ JWT | any | Yes |
| `/artifacts/{type}/{id}` | PUT | ✓ JWT | any | Yes |
| `/artifacts/{type}/{id}` | DELETE | ✓ JWT | admin | Yes |
| `/audit/logs` | GET | ✓ JWT | admin | No |
| `/artifact/byRegEx` | POST | ✗ | - | No |

### 3. Denial-of-Service (DoS) Protections

**Regex DoS (ReDoS) Prevention**
- All regex patterns validated before compilation
- Pattern length limited to 1000 characters
- Nested quantifiers detected and rejected (e.g., `(a+)+`, `(a*)*`)
- Invalid patterns rejected with HTTP 400
- **Endpoint**: `/artifact/byRegEx`

**Rate Limiting**
- Simple in-memory rate limiting (per-user, per-endpoint)
- Upload endpoint limited to 3 uploads per minute per user
- Exceeded limits return HTTP 429 (Too Many Requests)
- Production deployments should use Redis for distributed rate limiting

**File Size Limits**
- Upload payload validation (not yet integrated but available)
- 200MB maximum file size (configurable)
- Oversized files rejected with HTTP 413

### 4. Audit Logging

**Audit Trail** (`AuditLog` table)
- All sensitive operations logged with timestamp, user ID, action
- Columns: `id`, `action`, `user_id`, `resource`, `resource_type`, `success`, `metadata_json`, `created_at`
- Queryable via admin-only `/audit/logs` endpoint with filters

**Logged Actions**
- `registry.reset` - Entire registry reset to empty state
- `artifact.create` - New artifact uploaded
- `artifact.update` - Artifact metadata/URL changed
- `artifact.delete` - Artifact removed from registry

**Audit Data Protection**
- Sensitive fields NOT logged: token content, file payloads, user passwords
- Metadata includes safe operational context (domain name, artifact count, change flags)
- Failed operations logged with error class (not full stack trace)

### 5. Input Validation

**Regex Pattern Validation**
- Max length: 1000 characters
- Rejects invalid syntax
- Detects nested quantifiers to prevent ReDoS
- Validation function: `validate_regex_safe()`

**JSON Schema & Type Validation**
- Pydantic models enforce request payload structure
- Field types and constraints validated server-side
- Invalid payloads rejected with HTTP 422

**String Input Limits**
- Artifact names, types: max 255 characters (database schema)
- URLs: max 1024 characters
- All user inputs sanitized via SQLAlchemy ORM (parameterized queries)

### 6. HTTPS/TLS Configuration

**Current Status**: HTTP (development mode)

**Production Deployment Options**

**Option A: AWS Application Load Balancer (ALB)**
```
1. Enable HTTPS listener on ALB
2. Configure SSL certificate (ACM or custom)
3. ALB terminates TLS, forwards HTTP to EC2
4. EC2 app runs on HTTP (port 8000) with TLS offload at ALB
5. Security groups restrict inbound traffic to ALB only
```

**Option B: Nginx Reverse Proxy with Self-Signed Cert**
```bash
# Generate self-signed certificate (dev/testing only):
openssl req -x509 -newkey rsa:2048 -nodes -out /etc/nginx/cert.pem -keyout /etc/nginx/key.pem -days 365

# Nginx config at /etc/nginx/sites-available/default:
server {
    listen 443 ssl;
    server_name _;
    ssl_certificate /etc/nginx/cert.pem;
    ssl_certificate_key /etc/nginx/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Host $host;
    }
}

server {
    listen 80;
    return 301 https://$host$request_uri;
}
```

**Option C: Uvicorn with HTTPS (Not Recommended for Production)**
```bash
uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --ssl-keyfile=/path/to/key.pem \
  --ssl-certfile=/path/to/cert.pem
```

**⚠️ WARNING**: Current `deploy.sh` runs Uvicorn on HTTP (port 8000). **HTTPS REQUIRED for production**. Use ALB or Nginx reverse proxy.

## Code Implementation Details

### Files Added/Modified

**New Files**
- `phase2/src/packages_api/security.py` - JWT verification, RBAC, rate limiting, validators
- `phase2/src/packages_api/audit.py` - Audit logging helpers
- `phase2/src/packages_api/audit_api.py` - Audit log export endpoint
- `tests/test_security.py` - 26 security tests
- `tests/test_audit_basic.py` - 8 audit logging tests

**Modified Files**
- `phase2/src/packages_api/main.py` - Added JWT/RBAC to sensitive endpoints, integrated audit logging
- `phase2/src/packages_api/database.py` - Added `AuditLog` model
- `phase2/src/packages_api/schemas.py` - Added `AuditLogOut` schema
- `phase2/requirements.txt` - Added `PyJWT[crypto]==2.9.0`

### Key Functions

**Security Module (`packages_api/security.py`)**
```python
verify_jwt_token(authorization: str)       # Dependency: verify token signature, exp, iss, aud
require_admin(token: Dict)                 # Dependency: enforce admin role (403 if not)
require_role(role: str)                    # Factory: create role-checking dependency
validate_regex_safe(pattern: str)          # Validate regex (length, syntax, no ReDoS)
validate_file_size(bytes: int)             # Validate file size (200MB default)
check_rate_limit(key: str, limit: int)     # In-memory rate limiting per key
create_jwt_token(user_id, role)            # Create JWT (for dev/testing)
```

**Audit Module (`packages_api/audit.py`)**
```python
record_audit(db, action, user_id, resource, success, metadata)  # Log action
query_audit_logs(db, start, end, user_id, action, limit)       # Query with filters
```

## Testing

**Test Coverage**: 34 tests covering:
- JWT creation, verification, expiration, invalid tokens
- RBAC enforcement (admin/user roles)
- Regex validation (safe patterns, length limits, nested quantifiers)
- File size validation
- Rate limiting
- Audit logging (create, update, delete, reset)
- Integration tests (JWT + RBAC + audit)

**Running Tests**
```bash
cd /path/to/ece-30861-13-Copy
source ../../venv/bin/activate
DATABASE_URL="sqlite:///:memory:" python -m pytest tests/test_security.py tests/test_audit_basic.py -v
```

## Environment Variables (Production)

```bash
# JWT Configuration
export JWT_SECRET="<strong-random-secret-256-bits>"  # Required!
export JWT_ISSUER="ece-461-registry"
export JWT_AUDIENCE="ece-461-api"
export JWT_EXPIRATION_HOURS="24"

# Database
export DATABASE_URL="postgresql://user:password@host:5432/dbname"

# Optional: Dev mode only
# export JWT_SECRET="dev-secret"  # DO NOT USE IN PRODUCTION
```

## Threat Model Coverage

| STRIDE Category | Threat | Mitigation |
|----------------|--------|-----------|
| **Spoofing** | Fake JWT tokens | JWT signature verification (HS256) |
| **Tampering** | Modified token claims | Signature validation on every request |
| **Repudiation** | Deny actions taken | Audit logging with user ID + timestamp |
| **Information Disclosure** | Sensitive data in logs | No tokens/passwords in logs |
| **Denial of Service** | Regex ReDoS | Pattern validation, length limits, quantifier check |
| **Denial of Service** | Rapid uploads | Rate limiting per user (3/min) |
| **Denial of Service** | Large payloads | File size validation (200MB max) |
| **Elevation of Privilege** | Non-admin accessing admin endpoints | RBAC enforcement (role check) |
| **Elevation of Privilege** | Token expiration bypass | Expiration validation in verify_jwt_token |

## Known Limitations & Recommendations

1. **Rate Limiting**: In-memory storage not suitable for distributed deployments. Use Redis in production.
2. **HTTPS**: Currently HTTP-only. Implement TLS termination via ALB or Nginx (see above).
3. **Token Rotation**: No token refresh mechanism. Use short expiration (< 24 hours) and re-authenticate.
4. **Secrets Management**: `JWT_SECRET` must come from AWS Secrets Manager/Parameter Store, not env files.
5. **Audit Storage**: Append-only database. Implement regular backups and log rotation.
6. **IP Whitelisting**: Consider adding source IP validation for admin endpoints.

## Deployment Checklist

- [ ] Generate strong `JWT_SECRET` (256-bit random)
- [ ] Store `JWT_SECRET` in AWS Systems Manager Parameter Store or Secrets Manager
- [ ] Configure TLS/HTTPS (ALB or Nginx)
- [ ] Update `deploy.sh` with HTTPS proxy settings
- [ ] Set `DATABASE_URL` to production PostgreSQL
- [ ] Review audit logs regularly
- [ ] Test JWT token creation/verification with real tokens
- [ ] Test RBAC: verify admin vs user endpoints return 403
- [ ] Load test regex validation and rate limiting
- [ ] Set up CloudWatch alerts for failed auth attempts

## References

- STRIDE Threat Modeling: https://en.wikipedia.org/wiki/STRIDE_(security)
- JWT Best Practices: https://tools.ietf.org/html/rfc8725
- OWASP ReDoS Prevention: https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS
- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/
