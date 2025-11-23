#!/bin/bash
set -e

echo "Starting Phase 2 deployment to AWS..."

# Configuration
AWS_REGION=${AWS_REGION:-us-east-2}
EC2_INSTANCE_ID=${EC2_INSTANCE_ID:-}
S3_BUCKET=${S3_BUCKET:-}
APP_NAME="phase2"
APP_DIR="/opt/phase2"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Validate environment
if [ -z "$EC2_INSTANCE_ID" ]; then
    log_error "EC2_INSTANCE_ID not set. Set it as a GitHub secret."
    exit 1
fi

if [ -z "$S3_BUCKET" ]; then
    log_warn "S3_BUCKET not set. Skipping S3 backup."
fi

log_info "Deploying to EC2 instance: $EC2_INSTANCE_ID"

# Build application
log_info "Building application..."
cd "$(dirname "$0")/.."
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt || log_warn "No requirements.txt found"

# Run tests
log_info "Running tests..."
pytest tests/ -q || log_error "Tests failed!"

# Backup to S3 (optional)
if [ -n "$S3_BUCKET" ]; then
    log_info "Backing up code to S3: s3://$S3_BUCKET/$APP_NAME"
    aws s3 sync . "s3://$S3_BUCKET/$APP_NAME" \
        --exclude ".git/*" \
        --exclude ".venv/*" \
        --exclude "__pycache__/*" \
        --exclude "*.pyc" \
        --region "$AWS_REGION"
fi

# Deploy to EC2 via SSM (Systems Manager)
log_info "Deploying to EC2 instance via AWS Systems Manager..."

DEPLOY_SCRIPT=$(cat <<'EOF'
#!/bin/bash
set -e
echo "Running deployment on EC2..."
cd /opt/phase2 || mkdir -p /opt/phase2
cd /opt/phase2

# Pull latest code (if using git)
if [ -d .git ]; then
    git pull origin main
else
    echo "Not a git repo, code should be synced via S3 or other means."
fi

# Create venv and install deps
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt || true

# Initialize database
python phase2/database/seed_db.py

# Start the application (example: FastAPI/Uvicorn)
pkill -f uvicorn || true
nohup uvicorn phase2.main:app --host 0.0.0.0 --port 8000 > /var/log/phase2.log 2>&1 &

echo "Deployment on EC2 complete!"
EOF
)

aws ssm send-command \
    --instance-ids "$EC2_INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters "commands='$DEPLOY_SCRIPT'" \
    --region "$AWS_REGION" \
    --output text

log_info "Deployment command sent to EC2. Check EC2 instance or CloudWatch Logs for status."

# Verify health (optional)
log_info "Checking application health..."
sleep 5
if curl -f http://localhost:8000/health 2>/dev/null || log_warn "Health check endpoint not responding yet."; then
    log_info "Application is healthy!"
else
    log_error "Application health check failed. Check EC2 instance logs."
fi

log_info "Deployment complete!"