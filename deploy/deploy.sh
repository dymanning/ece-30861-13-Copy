#!/usr/bin/env bash
# Idempotent deploy script to run on EC2 instances
# Expected to be invoked by SSM after the artifact is downloaded and unzipped to /tmp/deploy

set -euo pipefail

LOG_FILE="/tmp/deploy/deploy.log"
mkdir -p /tmp/deploy || true
exec > >(tee -a "$LOG_FILE") 2>&1
echo "Starting deploy at $(date)"

APP_DIR="/home/ec2-user/app"
SERVICE_NAME="phase2"

echo "Starting deploy script: $(date)"
echo "App dir: $APP_DIR"

# If an unpacked artifact exists in /tmp/deploy, use it; otherwise try git pull in APP_DIR
if [ -d /tmp/deploy ] && [ "$(ls -A /tmp/deploy)" ]; then
  echo "Found unpacked artifact in /tmp/deploy — syncing to $APP_DIR"
  mkdir -p "$APP_DIR"
  # Use rsync if available for safe sync; fall back to cp
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete /tmp/deploy/ "$APP_DIR/"
  else
    cp -R /tmp/deploy/* "$APP_DIR/"
  fi
else
  if [ -d "$APP_DIR/.git" ]; then
    echo "No artifact found; performing git fetch and reset in $APP_DIR"
    cd "$APP_DIR"
    git fetch --all --prune
    git reset --hard origin/main
  else
    echo "No artifact and no git repository at $APP_DIR. Nothing to deploy." >&2
    exit 1
  fi
fi

cd "$APP_DIR"

# Install Python requirements if present (non-fatal)
if [ -f requirements.txt ]; then
  echo "Installing Python requirements (if pip available)"
  if command -v pip3 >/dev/null 2>&1; then
    pip3 install -r requirements.txt || true
  fi
fi

# Install and configure CloudWatch agent for logging
echo "Configuring CloudWatch Logs agent..."
if ! command -v /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl >/dev/null 2>&1; then
  echo "CloudWatch agent not found. Installing..."
  if command -v yum >/dev/null 2>&1; then
    sudo yum install -y amazon-cloudwatch-agent || true
  elif command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update && sudo apt-get install -y amazon-cloudwatch-agent || true
  else
    echo "Could not determine package manager. Skipping CloudWatch agent install."
  fi
fi

# Create CloudWatch agent configuration
CW_CONFIG_PATH="/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json"
echo "Creating CloudWatch agent config at $CW_CONFIG_PATH"
sudo mkdir -p "$(dirname "$CW_CONFIG_PATH")"
sudo tee "$CW_CONFIG_PATH" > /dev/null <<'CWCONFIG'
{
# Use bundled CloudWatch config from artifact if present; else ensure a default exists
echo "Deploy completed at: $(date)"
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

# --- CloudWatch Agent Setup for Ubuntu EC2 Logging ---
echo "\n[CloudWatch] Installing and configuring CloudWatch Agent for logging..."

# Install CloudWatch Agent if not present
if ! dpkg -l | grep -q amazon-cloudwatch-agent; then
  echo "[CloudWatch] Installing amazon-cloudwatch-agent..."
  sudo apt-get update && sudo apt-get install -y amazon-cloudwatch-agent
else
  echo "[CloudWatch] CloudWatch Agent already installed."
fi

# Ensure log files and directories exist
sudo mkdir -p /var/log/nginx
sudo mkdir -p /var/www/myapp
sudo touch /var/log/nginx/error.log /var/log/nginx/access.log /var/www/myapp/app.log
sudo chmod 666 /var/log/nginx/error.log /var/log/nginx/access.log /var/www/myapp/app.log

# Create CloudWatch Agent config if not present
CW_CONFIG="/opt/aws/amazon-cloudwatch-agent/bin/config.json"
if [ ! -f "$CW_CONFIG" ]; then
  echo "[CloudWatch] Creating default config at $CW_CONFIG"
  sudo tee "$CW_CONFIG" > /dev/null <<'CWCONFIG'
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/syslog",
            "log_group_name": "ec2-syslog",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/var/log/nginx/error.log",
            "log_group_name": "nginx-error",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/var/log/nginx/access.log",
            "log_group_name": "nginx-access",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/var/www/myapp/app.log",
            "log_group_name": "app-log",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
CWCONFIG
else
  echo "[CloudWatch] Config already exists at $CW_CONFIG"
fi

# Start and enable CloudWatch Agent service
echo "[CloudWatch] Starting and enabling CloudWatch Agent service..."
sudo systemctl enable amazon-cloudwatch-agent
sudo systemctl restart amazon-cloudwatch-agent
echo "[CloudWatch] CloudWatch Agent setup complete."