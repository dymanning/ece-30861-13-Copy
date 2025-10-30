# Quick Start Guide

Get your enumerate and search API running in 5 minutes!

## Prerequisites

- Node.js 20+
- PostgreSQL 14+ (or Docker)
- Git

## Step-by-Step Setup

### 1. Install Dependencies

```bash
cd phase2
npm install
```

### 2. Start Database (Docker - Easiest Option)

```bash
docker run -d \
  --name artifact-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=artifact_registry \
  -p 5432:5432 \
  postgres:14
```

Wait 10 seconds for database to initialize.

### 3. Configure Environment

```bash
cp .env.example .env
```

The defaults in `.env.example` work with the Docker setup above. No changes needed!

### 4. Set Up Database Schema + Sample Data

```bash
npm run setup
```

This runs migrations and inserts 10 sample artifacts for testing.

### 5. Start Server

```bash
npm run dev
```

Server starts at `http://localhost:3000`

### 6. Test It!

```bash
# Health check
curl http://localhost:3000/health

# Get all artifacts
curl -X POST http://localhost:3000/artifacts \
  -H "Content-Type: application/json" \
  -H "X-Authorization: test-token" \
  -d '[{"name": "*"}]'

# Search for "bert"
curl -X POST http://localhost:3000/artifact/byRegEx \
  -H "Content-Type: application/json" \
  -H "X-Authorization: test-token" \
  -d '{"regex": "bert"}'
```

## Success!

You should see JSON responses with artifact metadata.

---

## Sample Test Data

The `npm run setup` command inserts these sample artifacts:

1. **audience-classifier** (model) - Text classification
2. **bookcorpus** (dataset) - Books dataset
3. **google-research-bert** (code) - BERT implementation
4. **bert-base-uncased** (model) - BERT model
5. **openai-whisper** (code) - Speech recognition
6. **transformers** (code) - HuggingFace library
7. **gpt2** (model) - GPT-2 model
8. **yolo-v8** (model) - Object detection
9. **imagenet** (dataset) - Image dataset
10. **llama-2** (model) - Meta's LLM

---

## Troubleshooting

### "Database connection failed"

Make sure PostgreSQL is running:
```bash
docker ps | grep artifact-db
```

If not running:
```bash
docker start artifact-db
```

### "Port 3000 already in use"

Change port in `.env`:
```env
PORT=3001
```

### "Cannot find module"

Reinstall dependencies:
```bash
rm -rf node_modules package-lock.json
npm install
```

---

## Next Steps

1. **Integration Testing:** Work with Dylan to test CRUD + search together
2. **Production Setup:** Configure `.env` for AWS RDS
3. **Performance Testing:** Run load tests with larger datasets
4. **Documentation:** Share API examples with team

---

## Useful Commands

```bash
# Start fresh
docker stop artifact-db && docker rm artifact-db
# Then repeat setup steps

# View logs
tail -f logs/app.log

# Check database
docker exec -it artifact-db psql -U postgres -d artifact_registry
# Then: \dt (list tables), \d artifacts (describe table)

# Production build
npm run build
npm start
```

---

## API Endpoints Summary

| Endpoint | Method | Description | Status |
|----------|--------|-------------|--------|
| `/health` | GET | Health check | ✅ |
| `/artifacts` | POST | Enumerate with pagination | ✅ BASELINE |
| `/artifact/byRegEx` | POST | Regex search | ✅ BASELINE |
| `/artifact/byName/:name` | GET | Exact name search | ✅ NON-BASELINE |

---

**Questions?** Check the main README.md for detailed documentation.
