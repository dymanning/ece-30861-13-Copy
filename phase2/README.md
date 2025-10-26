# ECE 461 Phase 2 - Trustworthy Artifact Registry

## Enumerate & Search API Implementation

This implementation provides artifact enumeration and search functionality for the Trustworthy ML Artifact Registry.

**Implemented By:** [Your Name]
**Deliverable:** #1 - Baseline Functionality
**Endpoints:** POST /artifacts, POST /artifact/byRegEx, GET /artifact/byName/:name

---

## Features

### ✅ Implemented (BASELINE)

1. **POST /artifacts** - Enumerate artifacts with pagination

   - Supports multiple queries in single request
   - Wildcard search with `name: "*"`
   - Type filtering (model, dataset, code)
   - Offset-based pagination
   - DoS prevention (max results limit)
2. **POST /artifact/byRegEx** - Regex search

   - Searches artifact names AND README content
   - ReDoS attack prevention
   - PostgreSQL full-text search optimization
   - Result limits for performance
3. **GET /artifact/byName/:name** - Name search (NON-BASELINE)

   - Returns all artifacts with exact name match
   - Supports multiple artifacts with same name

### 🔒 Security Features

- Authentication middleware (X-Authorization header)
- ReDoS protection with safe-regex validation
- SQL injection prevention (parameterized queries)
- DoS prevention (query limits, timeouts)
- Request size limits

### ⚡ Performance Features

- PostgreSQL indexes for fast queries
- Full-text search (GIN indexes)
- Query timeout protection
- Connection pooling
- Efficient pagination

---

## Tech Stack

- **Runtime:** Node.js 20+
- **Language:** TypeScript
- **Framework:** Express.js
- **Database:** PostgreSQL 14+
- **Libraries:**
  - `pg` - PostgreSQL client
  - `winston` - Logging
  - `safe-regex` - ReDoS protection
  - `helmet` - Security headers
  - `cors` - CORS handling

---

## Project Structure

```
phase2/
├── src/
│   ├── config/
│   │   ├── config.ts          # Configuration loader
│   │   └── database.ts        # PostgreSQL connection pool
│   ├── routes/
│   │   └── artifacts.routes.ts
│   ├── controllers/
│   │   └── artifacts.controller.ts
│   ├── services/
│   │   └── artifacts.service.ts
│   ├── middleware/
│   │   ├── auth.middleware.ts
│   │   └── error.middleware.ts
│   ├── types/
│   │   └── artifacts.types.ts
│   ├── utils/
│   │   ├── logger.ts
│   │   ├── pagination.utils.ts
│   │   └── regex.utils.ts
│   ├── app.ts                 # Express app setup
│   └── server.ts              # Entry point
├── database/
│   ├── schema.sql             # Database schema
│   └── migrate.ts             # Migration runner
├── package.json
├── tsconfig.json
└── .env.example
```

---

## Setup Instructions

### Prerequisites

- Node.js 20+ and npm
- PostgreSQL 14+
- Git

### 1. Install Dependencies

```bash
cd phase2
npm install
```

### 2. Configure Environment

Copy `.env.example` to `.env` and update values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Server Configuration
PORT=3000
NODE_ENV=development

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/artifact_registry
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=artifact_registry
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
DATABASE_SSL=false

# Pagination Configuration
DEFAULT_PAGE_SIZE=100
MAX_PAGE_SIZE=100
MAX_TOTAL_RESULTS=10000

# Regex Search Configuration
MAX_REGEX_LENGTH=200
REGEX_TIMEOUT_MS=5000
MAX_REGEX_RESULTS=1000
```

### 3. Set Up Database

#### Option A: Local PostgreSQL

```bash
# Create database
createdb artifact_registry

# Run migrations
npm run migrate
```

#### Option B: Docker PostgreSQL(I used this one during testing)

```bash
# Start PostgreSQL container
docker run -d \
  --name artifact-registry-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=artifact_registry \
  -p 5432:5432 \
  postgres:14

# Wait for database to be ready
sleep 5

# Run migrations
npm run migrate
```

### 4. Start Development Server

```bash
npm run dev
```

Server will start at `http://localhost:3000`

### 5. Verify Installation

Check health endpoint:

```bash
curl http://localhost:3000/health
```

Expected response:

```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2024-10-25T12:00:00.000Z"
}
```

---

## Usage Examples

### 1. Enumerate All Artifacts

```bash
curl -X POST http://localhost:3000/artifacts \
  -H "Content-Type: application/json" \
  -H "X-Authorization: dummy-token" \
  -d '[{"name": "*"}]'
```

### 2. Enumerate with Type Filter

```bash
curl -X POST http://localhost:3000/artifacts \
  -H "Content-Type: application/json" \
  -H "X-Authorization: dummy-token" \
  -d '[{"name": "*", "types": ["model"]}]'
```

### 3. Enumerate Specific Artifact

```bash
curl -X POST http://localhost:3000/artifacts \
  -H "Content-Type: application/json" \
  -H "X-Authorization: dummy-token" \
  -d '[{"name": "bert-base-uncased"}]'
```

### 4. Pagination

```bash
# First page
curl -X POST "http://localhost:3000/artifacts?offset=0" \
  -H "Content-Type: application/json" \
  -H "X-Authorization: dummy-token" \
  -d '[{"name": "*"}]'

# Next page (use offset from response header)
curl -X POST "http://localhost:3000/artifacts?offset=100" \
  -H "Content-Type: application/json" \
  -H "X-Authorization: dummy-token" \
  -d '[{"name": "*"}]'
```

### 5. Regex Search

```bash
# Search for artifacts with "bert" in name or README
curl -X POST http://localhost:3000/artifact/byRegEx \
  -H "Content-Type: application/json" \
  -H "X-Authorization: dummy-token" \
  -d '{"regex": ".*bert.*"}'

# Case-insensitive search for "classifier"
curl -X POST http://localhost:3000/artifact/byRegEx \
  -H "Content-Type: application/json" \
  -H "X-Authorization: dummy-token" \
  -d '{"regex": "classifier"}'
```

### 6. Search by Name

```bash
curl -X GET "http://localhost:3000/artifact/byName/audience-classifier" \
  -H "X-Authorization: dummy-token"
```

---

## API Response Examples

### Success Response (200)

```json
[
  {
    "name": "audience-classifier",
    "id": "3847247294",
    "type": "model"
  },
  {
    "name": "bookcorpus",
    "id": "5738291045",
    "type": "dataset"
  }
]
```

### Error Responses

**400 Bad Request:**

```json
{
  "error": "BadRequestError",
  "message": "Invalid regex pattern",
  "statusCode": 400
}
```

**403 Forbidden:**

```json
{
  "error": "ForbiddenError",
  "message": "Missing X-Authorization header",
  "statusCode": 403
}
```

**404 Not Found:**

```json
{
  "error": "NotFoundError",
  "message": "No artifacts found matching the regex pattern",
  "statusCode": 404
}
```

**413 Payload Too Large:**

```json
{
  "error": "PayloadTooLargeError",
  "message": "Query would return too many results",
  "statusCode": 413
}
```

---

## Database Schema

Key tables and indexes:

```sql
-- Artifacts table
CREATE TABLE artifacts (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('model', 'dataset', 'code')),
    url TEXT NOT NULL,
    readme TEXT,  -- For regex search
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_artifacts_name ON artifacts(name);
CREATE INDEX idx_artifacts_type ON artifacts(type);
CREATE INDEX idx_artifacts_name_type ON artifacts(name, type);
CREATE INDEX idx_artifacts_fulltext ON artifacts 
    USING GIN (to_tsvector('english', name || ' ' || COALESCE(readme, '')));
```

---

## Integration with Team

### Dependencies on Other Components

1. **Dylan (CRUD Endpoints):**

   - Must populate `readme` field during artifact upload
   - Share database schema
   - Use same artifact ID format
2. **Ava (CI/CD):**

   - Provide `DATABASE_URL` environment variable
   - Set up AWS RDS PostgreSQL
   - Configure GitHub Actions
3. **Cecilia (Ingest & Metrics):**

   - No direct dependency
   - Metrics stored in `metadata` JSONB field

### Providing to Team

- Database schema (`database/schema.sql`)
- TypeScript types (`src/types/artifacts.types.ts`)
- Example queries for testing

---

## Testing

### Manual Testing

1. Start server: `npm run dev`
2. Use provided curl commands above
3. Check logs in `logs/app.log`

### Load Testing (Optional)

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test enumerate endpoint
ab -n 1000 -c 10 \
  -p enumerate.json \
  -T "application/json" \
  -H "X-Authorization: token" \
  http://localhost:3000/artifacts
```

---

## Performance Characteristics

### Query Performance (on 10,000 artifacts)

- Enumerate all: ~50-100ms
- Enumerate filtered: ~20-50ms
- Regex search (simple): ~50-150ms
- Name search: ~10-30ms
- Pagination (any offset): ~50-100ms

### Limits

- Page size: 100 items
- Max total results: 10,000
- Regex timeout: 5 seconds
- Max regex pattern length: 200 characters

---

## Known Limitations

1. **Authentication:** Stub implementation for Deliverable #1

   - Accepts any non-empty token
   - Real JWT validation needed for production
2. **Pagination:** Offset-based (not cursor-based)

   - Can skip items if data changes during pagination
   - Consider cursor-based for future
3. **Regex Complexity:** Limited to reasonably simple patterns

   - Very complex patterns may timeout
   - Full-text search used as pre-filter

---

## Troubleshooting

### Database Connection Errors

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Check credentials in .env
cat .env | grep DATABASE
```

### Migration Errors

```bash
# Drop and recreate database
dropdb artifact_registry
createdb artifact_registry
npm run migrate
```

### Port Already in Use

```bash
# Find process using port 3000
lsof -i :3000

# Kill process or change PORT in .env
```

---

## Deployment Notes

### AWS RDS Setup (Ava's Responsibility)

Required configurations:

- PostgreSQL 14+
- Public accessibility (for development)
- Security group: Allow inbound on 5432
- Provide `DATABASE_URL` to team

### Environment Variables for Production

```env
NODE_ENV=production
DATABASE_SSL=true
AUTH_ENABLED=true
LOG_LEVEL=info
```

---

## Questions for Team Meeting

1. **For Dylan:** When will README field be populated during upload?
2. **For Ava:** When will RDS be ready? Need connection string.
3. **For Cecilia:** Where should metrics be stored in database?
4. **For All:** Should we use shared dev database or local?

---

## Contact

**Implementer:** [Your Name]
**GitHub:** [Your GitHub URL]
**Email:** [Your Email]

**Last Updated:** October 25, 2025
