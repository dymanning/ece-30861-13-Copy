# Sensitive Model Monitoring - Setup & Testing Guide

## 🎯 Overview

This implementation adds security monitoring to artifact downloads. Node.js scripts validate artifacts before allowing downloads, with results logged to a monitoring history database.

---

## 📦 Components Implemented

### 1. **Security Scripts** (`security-scripts/`)

- ✅ `default-check.js` - Default security validation
- ✅ `size-limit-check.js` - Size limit validation
- ✅ `package.json` - Node.js dependencies

### 2. **Python Monitoring Module** (`phase2/src/packages_api/monitoring.py`)

- ✅ `run_security_check()` - Execute Node.js scripts via subprocess
- ✅ `save_monitoring_result()` - Log results to database
- ✅ `check_artifact_sensitivity()` - Check if artifact requires monitoring
- ✅ `MonitoringResult` class - Result container

### 3. **Database Schema** (`phase2/database/schema.sql`)

- ✅ Added `is_sensitive`, `monitoring_script`, `require_approval` to `artifacts` table
- ✅ Created `monitoring_history` table
- ✅ Created `monitoring_config` table
- ✅ Added indexes for performance

### 4. **FastAPI Integration** (`phase2/src/packages_api/main.py`)

- ✅ Integrated monitoring into `GET /packages/{pkg_id}` download endpoint
- ✅ Returns 403 if security check fails
- ✅ Logs all monitoring executions

---

## 🚀 Setup Instructions

### Step 1: Install Node.js Dependencies

```bash
cd security-scripts
npm install
```

This installs `minimist` for command-line argument parsing.

### Step 2: Update Database Schema

```bash
cd phase2

# Option A: Run migration (if using TypeScript migrate.ts)
npm run migrate

# Option B: Apply SQL directly
psql -U postgres -d artifact_registry -f database/schema.sql
```

This creates:

- `monitoring_history` table
- `monitoring_config` table
- New columns in `artifacts` table

### Step 3: Test Security Scripts

```bash
cd security-scripts

# Test with safe artifact
node default-check.js --artifact-id test123 --name safe-model --type model
# Expected: Exit code 0, JSON output with "allow"

# Test with suspicious artifact
node default-check.js --artifact-id test456 --name malware-backdoor --type model
# Expected: Exit code 2, JSON output with "block"

# Test size limits
node size-limit-check.js --artifact-id test789 --name big-model --size 5000000000
# Expected: Exit code 1 (warning), JSON output
```

### Step 4: Mark Artifacts as Sensitive

```sql
-- Mark specific artifacts for monitoring
UPDATE artifacts 
SET is_sensitive = TRUE,
    monitoring_script = 'default-check.js'
WHERE name LIKE '%sensitive%' OR type = 'model';

-- Or mark all artifacts
UPDATE artifacts SET is_sensitive = TRUE;
```

### Step 5: Test FastAPI Integration

```bash
# Start FastAPI server
cd phase2/src/packages_api
uvicorn main:app --reload --port 8000
```

Then test download:

```bash
# Should work (non-sensitive artifact)
curl http://localhost:8000/packages/1

# Should block if artifact is sensitive and named suspiciously
# First, create sensitive artifact in DB:
psql -U postgres -d artifact_registry -c "
INSERT INTO artifacts (id, name, type, url, is_sensitive) 
VALUES ('test999', 'malware-model', 'model', 'http://example.com', TRUE)
ON CONFLICT (id) DO UPDATE SET is_sensitive = TRUE;
"

# Then try to download (should get 403)
curl -v http://localhost:8000/packages/test999
```

---

## 🧪 Testing Guide

### Unit Tests (Python)

```bash
cd phase2/src/packages_api

# Run monitoring tests
python -m pytest test_monitoring.py -v

# Expected output:
# test_safe_artifact PASSED
# test_malicious_artifact PASSED
# test_missing_script PASSED
# test_result_to_dict PASSED
# test_output_truncation PASSED
```

### Integration Tests

#### Test 1: Safe Artifact Download

```bash
# 1. Create safe artifact
psql -c "INSERT INTO artifacts (id, name, type, url, is_sensitive) 
         VALUES ('safe001', 'bert-model', 'model', 'http://example.com', TRUE)"

# 2. Try download
curl http://localhost:8000/packages/safe001

# Expected: 200 OK, file downloads
# Check monitoring history:
psql -c "SELECT * FROM monitoring_history WHERE artifact_id='safe001'"
```

#### Test 2: Blocked Download

```bash
# 1. Create suspicious artifact
psql -c "INSERT INTO artifacts (id, name, type, url, is_sensitive) 
         VALUES ('bad001', 'virus-backdoor', 'model', 'http://example.com', TRUE)"

# 2. Try download
curl -v http://localhost:8000/packages/bad001

# Expected: 403 Forbidden with JSON error
# {
#   "error": "DownloadBlocked",
#   "message": "Artifact failed security monitoring check",
#   "monitoring": {
#     "exit_code": 2,
#     "action": "blocked",
#     "findings": [...]
#   }
# }
```

#### Test 3: Warning (Allowed with Log)

```bash
# 1. Create artifact with warning condition
psql -c "INSERT INTO artifacts (id, name, type, url, is_sensitive) 
         VALUES ('warn001', 'x' || repeat('y', 300), 'model', 'http://example.com', TRUE)"

# 2. Try download
curl http://localhost:8000/packages/warn001

# Expected: 200 OK (allowed), but warning logged
# Check history:
psql -c "SELECT action_taken, exit_code, stdout FROM monitoring_history 
         WHERE artifact_id='warn001'"
# Should show action='warned', exit_code=1
```

---

## 🔍 Monitoring History Queries

### View All Monitoring Events

```sql
SELECT 
    mh.id,
    mh.artifact_id,
    a.name as artifact_name,
    mh.script_name,
    mh.exit_code,
    mh.action_taken,
    mh.execution_duration_ms,
    mh.executed_at,
    mh.user_id
FROM monitoring_history mh
JOIN artifacts a ON a.id = mh.artifact_id
ORDER BY mh.executed_at DESC
LIMIT 20;
```

### Check Blocked Downloads

```sql
SELECT 
    artifact_id,
    COUNT(*) as block_count,
    MAX(executed_at) as last_blocked
FROM monitoring_history
WHERE action_taken = 'blocked'
GROUP BY artifact_id
ORDER BY block_count DESC;
```

### Performance Stats

```sql
SELECT 
    script_name,
    COUNT(*) as executions,
    AVG(execution_duration_ms) as avg_duration_ms,
    MAX(execution_duration_ms) as max_duration_ms,
    COUNT(CASE WHEN action_taken = 'blocked' THEN 1 END) as blocks,
    COUNT(CASE WHEN action_taken = 'error' THEN 1 END) as errors
FROM monitoring_history
GROUP BY script_name;
```

### User Activity

```sql
SELECT 
    user_id,
    COUNT(*) as downloads_attempted,
    COUNT(CASE WHEN action_taken = 'blocked' THEN 1 END) as blocked,
    COUNT(CASE WHEN action_taken = 'allowed' THEN 1 END) as allowed
FROM monitoring_history
WHERE user_id IS NOT NULL
GROUP BY user_id
ORDER BY downloads_attempted DESC;
```

---

## 🎨 Custom Security Scripts

### Creating a New Script

1. Create `security-scripts/custom-check.js`:

```javascript
#!/usr/bin/env node
const minimist = require('minimist');
const args = minimist(process.argv.slice(2));

// Your validation logic here
const result = {
  timestamp: new Date().toISOString(),
  artifact_id: args['artifact-id'],
  findings: [],
  recommendation: 'allow'
};

console.log(JSON.stringify(result, null, 2));
process.exit(0); // 0=allow, 1=warn, 2=block
```

2. Assign to artifact:

```sql
UPDATE artifacts 
SET monitoring_script = 'custom-check.js'
WHERE id = 'your-artifact-id';
```

---

## 🔧 Configuration

### Monitoring Settings (Database)

```sql
-- View current config
SELECT * FROM monitoring_config;

-- Update timeout
UPDATE monitoring_config 
SET value = '10000' 
WHERE key = 'script_timeout_ms';

-- Update max output length
UPDATE monitoring_config 
SET value = '50000' 
WHERE key = 'max_output_length';
```

### Environment Variables

In Python code, you can add environment-based config:

```python
# monitoring.py
import os

SCRIPT_TIMEOUT_SECONDS = int(os.getenv('MONITORING_TIMEOUT', '5'))
MAX_OUTPUT_LENGTH = int(os.getenv('MONITORING_MAX_OUTPUT', '10000'))
```

---

## 📊 Exit Code Reference

| Exit Code | Meaning        | Action              | HTTP Status             |
| --------- | -------------- | ------------------- | ----------------------- |
| 0         | Safe           | Allow download      | 200 OK                  |
| 1         | Warning        | Allow with log      | 200 OK                  |
| 2+        | Blocked        | Deny download       | 403 Forbidden           |
| 124       | Timeout        | Deny (safe default) | 503 Service Unavailable |
| 127       | Node not found | Error               | 500 Internal Error      |
| 255       | Script error   | Error               | 500 Internal Error      |

---

## 🐛 Troubleshooting

### Script Not Found

```
Error: Security script not found: default-check.js
```

**Fix:**

```bash
# Check script exists
ls -l security-scripts/default-check.js

# Verify SECURITY_SCRIPTS_DIR path in monitoring.py
python -c "from pathlib import Path; print(Path(__file__).parent.parent.parent.parent / 'security-scripts')"
```

### Node.js Not Found

```
Error: Node.js executable not found
```

**Fix:**

```bash
# Install Node.js
# Windows: Download from nodejs.org
# Linux: sudo apt install nodejs
# Mac: brew install node

# Verify installation
node --version
which node
```

### Database Connection Error

```
Error: relation "monitoring_history" does not exist
```

**Fix:**

```bash
# Run migration
cd phase2
npm run migrate

# Or apply SQL directly
psql -U postgres -d artifact_registry -f database/schema.sql
```

### Timeout Errors

```
Script execution timed out after 5 seconds
```

**Fix:**

```python
# Increase timeout in monitoring.py
SCRIPT_TIMEOUT_SECONDS = 10
```

---

## 📈 Performance Considerations

### Script Execution Time

- Default timeout: 5 seconds
- Average execution: 100-300ms
- Target: < 500ms for production

### Database Impact

- Each download creates 1 monitoring_history row
- Typical row size: 1-5 KB
- Use partitioning for high-volume systems

### Optimization Tips

1. **Cache script results** (1 hour TTL):

```python
# Add to monitoring.py
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_security_check(artifact_id, artifact_name):
    return run_security_check(artifact_id, artifact_name)
```

2. **Async monitoring** (for non-blocking):

```python
import asyncio

async def async_run_security_check(...):
    # Run in thread pool
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_security_check, ...)
```

3. **Batch cleanup** (archive old history):

```sql
-- Archive history older than 90 days
DELETE FROM monitoring_history 
WHERE executed_at < NOW() - INTERVAL '90 days';
```

---

## ✅ Verification Checklist

- [ ] Node.js installed and in PATH
- [ ] `security-scripts/node_modules` exists (ran `npm install`)
- [ ] Database schema updated with monitoring tables
- [ ] At least one artifact marked as `is_sensitive = TRUE`
- [ ] FastAPI server running
- [ ] Can execute scripts manually: `node security-scripts/default-check.js --id test --name test`
- [ ] Download endpoint returns 403 for suspicious artifacts
- [ ] Monitoring history records created in database
- [ ] Unit tests pass: `pytest test_monitoring.py`
