# Security Monitoring Scripts

Node.js scripts for validating artifacts before download.

## Installation

```bash
cd security-scripts
npm install
```

## Available Scripts

### 1. default-check.js

Default security validation script. Checks for:
- Suspicious name patterns (malware, backdoor, etc.)
- Invalid artifact types
- Name length limits
- Special characters

**Usage:**
```bash
node default-check.js --artifact-id 12345 --name my-model --type model
```

**Exit Codes:**
- `0` - Safe to download
- `1` - Warning (allow with log)
- `2` - Block download

### 2. size-limit-check.js

Validates artifact size against deployment limits.

**Usage:**
```bash
node size-limit-check.js --artifact-id 12345 --name large-model --size 5000000000
```

## Creating Custom Scripts

Security scripts must:
1. Accept command-line arguments: `--artifact-id`, `--name`, `--type`
2. Output JSON to stdout with findings
3. Exit with appropriate code (0=allow, 1=warn, 2=block)
4. Complete within 5 seconds (timeout)

**Example Output:**
```json
{
  "timestamp": "2025-11-30T10:00:00.000Z",
  "artifact_id": "12345",
  "artifact_name": "test-model",
  "findings": [
    {
      "severity": "warning",
      "check": "name_length",
      "message": "Name exceeds recommended length"
    }
  ],
  "recommendation": "allow"
}
```

## Testing

```bash
# Test default check with safe name
node default-check.js --id test123 --name safe-model --type model

# Test with suspicious name
node default-check.js --id test456 --name malware-model --type model

# Test size limits
node size-limit-check.js --id test789 --name huge-model --size 50000000000
```

## Integration

Scripts are called by the Python FastAPI server before artifact downloads:

```python
from monitoring import run_security_check

result = run_security_check(
    artifact_id="12345",
    artifact_name="my-model",
    artifact_type="model"
)

if not result.is_allowed():
    # Block download
    raise HTTPException(status_code=403, detail="Security check failed")
```

## Script Configuration

Scripts are configured per-artifact in the database:

```sql
UPDATE artifacts 
SET is_sensitive = TRUE,
    monitoring_script = 'default-check.js'
WHERE id = '12345';
```

## Monitoring History

All script executions are logged to `monitoring_history` table:

```sql
SELECT 
    artifact_id,
    script_name,
    exit_code,
    action_taken,
    executed_at
FROM monitoring_history
ORDER BY executed_at DESC;
```
