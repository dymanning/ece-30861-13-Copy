# Security Quick Reference Guide

## For Developers

### Testing with JWT Tokens

```python
from packages_api.security import create_jwt_token

# Create tokens for testing
admin_token = create_jwt_token("admin_user", role="admin", expires_in_hours=1)
user_token = create_jwt_token("regular_user", role="user", expires_in_hours=1)

print(f"Admin: {admin_token}")
print(f"User: {user_token}")
```

### Protected Endpoints & Required Roles

| Endpoint | Method | Auth Required | Min Role | Example |
|----------|--------|---------------|----------|---------|
| `/reset` | DELETE | ✅ | admin | `curl -X DELETE -H "X-Authorization: Bearer $TOKEN" ...` |
| `/artifact/{type}` | POST | ✅ | any | Upload artifact - requires valid token |
| `/artifacts/{type}/{id}` | PUT | ✅ | any | Update artifact metadata |
| `/artifacts/{type}/{id}` | DELETE | ✅ | admin | Delete artifact - admin only |
| `/audit/logs` | GET | ✅ | admin | Query audit logs - admin only |
| `/artifact/byRegEx` | POST | ✅ | any | Search by regex (no admin required) |
| `/artifact/byName/{name}` | GET | ❌ | - | Read-only, no auth required |
| `/artifacts` | POST | ❌ | - | List artifacts, no auth required |

### Common HTTP Status Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | Request successful |
| 201 | Created | Artifact successfully created |
| 400 | Bad Request | Invalid regex pattern, malformed input |
| 401 | Unauthorized | Missing, invalid, or expired JWT token |
| 403 | Forbidden | Token valid but user lacks required role (not admin) |
| 404 | Not Found | Artifact/resource doesn't exist |
| 413 | Payload Too Large | File exceeds 200MB limit |
| 429 | Too Many Requests | Rate limit exceeded (3 uploads/min per user) |
| 500 | Server Error | Database error, unexpected failure |

### Testing in Development

```bash
# Set up environment
export JWT_SECRET="dev-secret-key-not-for-production"
export DATABASE_URL="sqlite:///./test.db"

# Create admin token
ADMIN_TOKEN=$(python -c "
from packages_api.security import create_jwt_token
print(create_jwt_token('admin', 'admin'))
")

# Create user token
USER_TOKEN=$(python -c "
from packages_api.security import create_jwt_token
print(create_jwt_token('user1', 'user'))
")

# Test reset (admin only)
curl -X DELETE \
  -H "X-Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/reset

# Test create artifact (any logged-in user)
curl -X POST \
  -H "X-Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://huggingface.co/gpt2"}' \
  http://localhost:8000/artifact/model

# Test delete artifact (admin only)
curl -X DELETE \
  -H "X-Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/artifacts/model/artifact-123

# Test unsafe regex (should fail)
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"regex": "(a+)+"}' \
  http://localhost:8000/artifact/byRegEx
# Returns: 400 Bad Request

# Query audit logs
curl -H "X-Authorization: Bearer $ADMIN_TOKEN" \
  "http://localhost:8000/audit/logs?action=artifact.delete&limit=10"
```

### Common Errors & Fixes

**401 Unauthorized: Missing authentication token**
- Issue: No X-Authorization header
- Fix: Add header: `X-Authorization: Bearer <token>`

**401 Unauthorized: Token has expired**
- Issue: Token creation time is past expiration
- Fix: Recreate token with fresh timestamp

**401 Unauthorized: Invalid token**
- Issue: Token is malformed or JWT_SECRET mismatch
- Fix: Ensure JWT_SECRET env var matches token signing secret

**403 Forbidden: Admin privileges required**
- Issue: User role is not "admin"
- Fix: Create token with `role="admin"`: `create_jwt_token(user_id, role="admin")`

**400 Bad Request: Regex pattern contains nested quantifiers**
- Issue: Regex has ReDoS vulnerability (e.g., `(a+)+`)
- Fix: Rewrite regex without nested quantifiers (e.g., `a+`)

**400 Bad Request: Regex pattern exceeds 1000 character limit**
- Issue: Regex pattern too long
- Fix: Simplify regex pattern to < 1000 chars

**429 Too Many Requests: Rate limit exceeded**
- Issue: User uploaded 3+ artifacts in last 60 seconds
- Fix: Wait 1 minute before uploading again

### Audit Log Queries

```python
from packages_api.audit import query_audit_logs
from datetime import datetime, timedelta

# Query all deletes by admin
logs = query_audit_logs(db, action="artifact.delete", user_id="admin")

# Query last hour's activity
last_hour = datetime.utcnow() - timedelta(hours=1)
logs = query_audit_logs(db, start=last_hour)

# Query specific user's uploads
logs = query_audit_logs(db, action="artifact.create", user_id="user123", limit=100)

# Print audit trail
for log in logs:
    print(f"{log.created_at} - {log.action} by {log.user_id}: {log.success}")
```

## For DevOps/Deployment

### Required Environment Variables (Production)

```bash
# REQUIRED - must be strong random value (not "dev-secret")
JWT_SECRET="<256-bit-random-secret>"

# Database - must be PostgreSQL, not SQLite
DATABASE_URL="postgresql://user:password@host:5432/database"

# Optional - defaults shown
JWT_ISSUER="ece-461-registry"
JWT_AUDIENCE="ece-461-api"
JWT_EXPIRATION_HOURS="24"
```

### Generate JWT_SECRET (Production)

```bash
# Generate 256-bit random secret
openssl rand -hex 32
# Example output: a1b2c3d4e5f6... (use this as JWT_SECRET)

# Store in AWS Systems Manager Parameter Store
aws ssm put-parameter \
  --name /phase2/JWT_SECRET \
  --value "<secret>" \
  --type SecureString \
  --region us-east-2

# Retrieve in deploy script
JWT_SECRET=$(aws ssm get-parameter --name /phase2/JWT_SECRET --with-decryption --query 'Parameter.Value' --output text)
export JWT_SECRET
```

### Deploy Checklist

- [ ] `JWT_SECRET` is strong random value (not "dev-secret")
- [ ] `DATABASE_URL` points to production PostgreSQL
- [ ] HTTPS/TLS configured (ALB or Nginx)
- [ ] Security groups restrict access to app (ALB only)
- [ ] CloudWatch logs configured for app output
- [ ] Audit logs stored in RDS with backups
- [ ] Test JWT token creation with real secret
- [ ] Test RBAC: user tokens get 403 on admin endpoints
- [ ] Load test: verify rate limiting works
- [ ] Monitor: CloudWatch alerts for 401/403 errors

### HTTPS Configuration

**Option 1: AWS ALB (Recommended)**
- ALB listens on 443 (HTTPS)
- ALB certificate from ACM
- ALB forwards to EC2 on 8000 (HTTP)
- Security group: allow ALB → EC2:8000 only

**Option 2: Nginx Reverse Proxy**
- See SECURITY.md for full Nginx config
- Nginx listens on 443 (HTTPS)
- Nginx forwards to localhost:8000 (HTTP)
- Self-signed cert for dev, real cert for prod

**⚠️ NEVER**: Run on plain HTTP in production. JWT tokens and audit data would be exposed.

### Troubleshooting

**App won't start**: Check JWT_SECRET and DATABASE_URL are set
```bash
echo $JWT_SECRET
echo $DATABASE_URL
```

**Audit logs not appearing**: Verify database tables created
```bash
python phase2/database/seed_db.py  # Creates tables
```

**Tests failing**: Ensure DATABASE_URL for testing is set
```bash
DATABASE_URL="sqlite:///:memory:" python -m pytest tests/test_security.py -v
```

---

**Need Help?** See `SECURITY.md` for comprehensive documentation.
