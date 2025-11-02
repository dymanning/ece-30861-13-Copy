# Packages API (FastAPI)

Minimal FastAPI app providing CRUD endpoints for model packages stored in S3
and referenced from PostgreSQL (RDS) via SQLAlchemy.

Environment variables (placeholders):

- DATABASE_URL - SQLAlchemy DB URL (postgresql://user:pass@host:5432/db)
- AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY - AWS credentials (or use IAM role)
- AWS_REGION - AWS region (default us-east-1)
- S3_BUCKET_NAME - S3 bucket to store packages

Quick start:

1. pip install -r src/packages_api/requirements.txt
2. set env vars
3. run with uvicorn:

```bash
uvicorn src.packages_api.main:app --reload
```

Notes:
- This example is minimal. For production add auth, better error handling,
  retries, logging, and secrets management.
