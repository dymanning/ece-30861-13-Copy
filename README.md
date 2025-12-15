Trustworthy Model Registry


Overview

The Trustworthy Model Registry is a secure and auditable system for managing machine learning models within an organization. It provides features such as model versioning, role-based access control (RBAC), secure authentication, and audit logging. The registry ensures that models are stored, retrieved, and updated in a way that meets security and compliance requirements.

Key features:
Model Storage: Upload and store models with metadata.
Role-Based Access Control (RBAC): Restrict actions to authorized users (e.g., admin, contributor, viewer).
Audit Logging: Record all model-related actions for traceability.
Secure Authentication: JWT-based login with token validation.
API-First Design: Interact with the registry via RESTful API endpoints.

Prerequisites

Python 3.12+
FastAPI
SQLAlchemy
SQLite (default) or PostgreSQL for production
Uvicorn for running the server
Optional: AWS credentials for S3 storage integration if using cloud model storage.

Configuration

Environment Variables: Create a .env file with the following variables:
DATABASE_URL=sqlite:///./registry.db   # or PostgreSQL connection string
JWT_SECRET_KEY=your_secret_key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
ADMIN_USERNAME=admin_user
ADMIN_PASSWORD=secure_password
S3_BUCKET_NAME=your_s3_bucket_name      # optional
AWS_ACCESS_KEY_ID=your_access_key       # optional
AWS_SECRET_ACCESS_KEY=your_secret_key   # optional

Database Initialization:
python initialize_db.py
This will create the required tables and optionally seed an admin user.

RBAC Setup:
Roles are pre-configured as: admin, contributor, viewer. Admin users can manage roles, contributors can upload models, viewers can only read.

Deployment

Local Development
# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn main:app --reload
The API will be available at http://127.0.0.1:8000.
Swagger UI documentation: http://127.0.0.1:8000/docs

Production Deployment
Use a production-ready ASGI server (e.g., Uvicorn with Gunicorn or Hypercorn).
Configure HTTPS using a reverse proxy (e.g., Nginx) and valid SSL certificates.
Set environment variables securely and configure cloud storage if needed.
Example Gunicorn command:
gunicorn -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000 --workers 4
Interacting with the Registry

API Endpoints

Authentication:
POST /login → Obtain JWT access token
POST /register → Register new users (admin only for production)
Model Management:
POST /models → Upload a new model (contributors/admin)
GET /models → List all models (all roles)
GET /models/{id} → Retrieve a specific model
DELETE /models/{id} → Delete a model (admin only)
Audit Logs:
GET /audit-logs → View all logged actions (admin only)
Example cURL Request
# Login and get token
curl -X POST "http://127.0.0.1:8000/login" -H "Content-Type: application/json" -d '{"username":"admin","password":"secure_password"}'

# Upload a model
curl -X POST "http://127.0.0.1:8000/models" -H "Authorization: Bearer <token>" -F "file=@model.pkl"

Security Considerations

Always use strong, unique secrets for JWT signing.
Enable HTTPS in production to prevent token interception.
Monitor audit logs to detect suspicious activity.
Limit file upload size to prevent denial-of-service attacks.
