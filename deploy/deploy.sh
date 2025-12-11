#!/usr/bin/env bash
# Idempotent deploy script to run on EC2 instances (SSM-friendly)
# Designed to be invoked via AWS Systems Manager (SSM) or run locally.
#
# Behavior and rationale:
# - SSM captures stdout/stderr of the command it runs. To guarantee SSM
#   can stream logs immediately we redirect ALL stdout/stderr at the top
#   of the script to a persistent deploy log (`/tmp/deploy/deploy.log`) and
#   also preserve stdout so SSM continues to receive output in real time.
# - We append logs to `/var/www/myapp/app.log` as well so the CloudWatch
#   agent (which tails files) can pick up deploy activity.
# - Script is idempotent: repeated runs are safe. We use `mkdir -p`, `touch`,
#   `rsync --delete` and non-fatal install steps.
# - The script detects whether it runs as root; when not root it uses `sudo`
#   for privileged operations so it works both under SSM (root) and locally.
# - CloudWatch agent setup/reload runs after logging is configured and is
#   executed in a non-blocking, best-effort way so it doesn't stall SSM.

set -euo pipefail

# Determine sudo usage: SSM runs commands as root by default.
if [ "$(id -u)" -eq 0 ]; then
  SUDO=""
else
  SUDO="sudo"
fi

LOG_DIR="/tmp/deploy"
LOG_FILE="$LOG_DIR/deploy.log"
APP_LOG_DIR="/var/www/myapp"
APP_LOG="$APP_LOG_DIR/app.log"

# Ensure log directories/files exist immediately (idempotent)
mkdir -p "$LOG_DIR" || true
$SUDO mkdir -p "$APP_LOG_DIR" || true
$SUDO touch "$APP_LOG" || true
$SUDO chmod 666 "$APP_LOG" || true

# If invoked via sudo from a non-root user, make sure that user can access the app log
if [ -n "${SUDO_USER:-}" ]; then
  $SUDO chown "${SUDO_USER}:${SUDO_USER}" "$APP_LOG" || true
fi

# Redirect ALL stdout/stderr at the very top. This preserves real-time output
# to the original stdout (so SSM can capture it) while appending to both the
# deploy log and the persistent application log. Stderr is merged into stdout.
exec > >(tee -a "$LOG_FILE" "$APP_LOG") 2>&1

echo "=== Deploy script started at $(date -u) ==="

APP_DIR="/home/ec2-user/app"
SERVICE_NAME="phase2"

echo "App dir: $APP_DIR"

# If an unpacked artifact exists in /tmp/deploy, sync it to the app dir
if [ -d /tmp/deploy ] && [ "$(ls -A /tmp/deploy)" ]; then
  echo "Found unpacked artifact in /tmp/deploy — syncing to $APP_DIR"
  mkdir -p "$APP_DIR"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete /tmp/deploy/ "$APP_DIR/"
  else
    # Fallback: copy and remove stale files
    rm -rf "$APP_DIR"/* || true
    cp -R /tmp/deploy/* "$APP_DIR/"
  fi
else
  if [ -d "$APP_DIR/.git" ]; then
    echo "No artifact found; performing git fetch and reset in $APP_DIR"
    cd "$APP_DIR"
    git fetch --all --prune || true
    git reset --hard origin/main || true
  else
    echo "No artifact and no git repository at $APP_DIR. Nothing to deploy." >&2
    exit 1
  fi
fi

cd "$APP_DIR" || { echo "Failed to cd to $APP_DIR"; exit 1; }

# Install Python requirements if present (non-fatal)
if [ -f requirements.txt ]; then
  echo "Installing Python requirements (non-fatal)"
  if command -v pip3 >/dev/null 2>&1; then
    pip3 install --upgrade pip setuptools wheel --disable-pip-version-check || true
    pip3 install -r requirements.txt || true
  else
    echo "pip3 not available; skipping requirements install"
  fi
fi

# Idempotent DB seed (if provided)
if [ -f phase2/database/seed_db.py ]; then
  echo "Running database seed (best-effort)"
  if command -v python3 >/dev/null 2>&1; then
    python3 phase2/database/seed_db.py || echo "Seed script failed (continuing)"
  fi
fi

# CloudWatch Agent setup — best-effort, non-blocking where possible
echo "Configuring CloudWatch Logs agent (best-effort)"
if ! command -v /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl >/dev/null 2>&1; then
  echo "CloudWatch agent not present — attempting install"
  if command -v yum >/dev/null 2>&1; then
    $SUDO yum install -y amazon-cloudwatch-agent || echo "yum install failed (continuing)"
  elif command -v apt-get >/dev/null 2>&1; then
    $SUDO DEBIAN_FRONTEND=noninteractive apt-get update -y || true
    $SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y amazon-cloudwatch-agent || echo "apt-get install failed (continuing)"
  else
    echo "No supported package manager; skipping agent install"
  fi
fi

# Write (idempotent) CloudWatch agent config that tails our application log
CW_CONFIG_PATH="/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json"
$SUDO mkdir -p "$(dirname "$CW_CONFIG_PATH")" || true
$SUDO tee "$CW_CONFIG_PATH" > /dev/null <<'CWCONFIG'
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/www/myapp/app.log",
            "log_group_name": "phase2-app",
            "log_stream_name": "{instance_id}",
            "timestamp_format": "%Y-%m-%d %H:%M:%S"
          }
        ]
      }
    }
  }
}
CWCONFIG

# Start/reload the agent using the ctl helper; it returns quickly and won't block SSM
if /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl --help >/dev/null 2>&1; then
  echo "Starting/reloading CloudWatch Agent (fetch-config + start)"
  $SUDO /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:$CW_CONFIG_PATH -s || echo "Agent ctl failed (continuing)"
else
  echo "ctl helper not available; attempting systemctl restart (best-effort)"
  $SUDO systemctl enable amazon-cloudwatch-agent || true
  $SUDO systemctl restart amazon-cloudwatch-agent || echo "systemctl restart failed (continuing)"
fi

# ============= HTTPS/TLS CONFIGURATION =============
# IMPORTANT: This application now requires HTTPS in production.
# The app runs on HTTP (port 8000) internally but MUST be behind TLS termination.
#
# Choose ONE of the following approaches:
#
# OPTION 1: AWS Application Load Balancer (ALB) - RECOMMENDED
#   - Configure HTTPS listener on ALB (port 443)
#   - Associate SSL certificate from AWS Certificate Manager (ACM)
#   - ALB terminates TLS and forwards HTTP to EC2 instance
#   - Set security group to allow only ALB on port 8000 (no direct internet access)
#
# OPTION 2: Nginx Reverse Proxy with Self-Signed Certificate
#   - Install nginx: sudo yum install nginx (or apt-get on Ubuntu)
#   - Generate self-signed cert (dev only):
#     sudo openssl req -x509 -newkey rsa:2048 -nodes \
#       -out /etc/nginx/cert.pem -keyout /etc/nginx/key.pem -days 365
#   - Configure /etc/nginx/sites-available/default (see SECURITY.md for full config)
#   - Run: sudo systemctl restart nginx
#   - Nginx listens on 443 (HTTPS), forwards to app on 8000 (HTTP)
#
# OPTION 3: Uvicorn with SSL (Development Only - NOT for Production)
#   - Install python ssl dependencies
#   - Run: uvicorn main:app --ssl-keyfile=key.pem --ssl-certfile=cert.pem
#
# ⚠️  WARNING: If none of these are configured, the API runs on plain HTTP!
#     This allows JWT tokens and sensitive data to be intercepted.
#     See SECURITY.md for detailed HTTPS setup instructions.
#

# Optionally ensure CloudWatch Log Group exists (if aws CLI is available)
CREATE_LOG_GROUP=${CREATE_LOG_GROUP:-true}
LOG_RETENTION_DAYS=${LOG_RETENTION_DAYS:-14}
if [ "$CREATE_LOG_GROUP" = "true" ] && command -v aws >/dev/null 2>&1; then
  AWS_REGION=${AWS_REGION:-us-east-2}
  LOG_GROUP="phase2-app"
  if aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP" --region "$AWS_REGION" --no-cli-pager | grep -q 'logGroupName'; then
    echo "Log group $LOG_GROUP exists; ensuring retention"
    aws logs put-retention-policy --log-group-name "$LOG_GROUP" --retention-in-days "$LOG_RETENTION_DAYS" --region "$AWS_REGION" || true
  else
    echo "Creating log group $LOG_GROUP"
    aws logs create-log-group --log-group-name "$LOG_GROUP" --region "$AWS_REGION" || true
    aws logs put-retention-policy --log-group-name "$LOG_GROUP" --retention-in-days "$LOG_RETENTION_DAYS" --region "$AWS_REGION" || true
  fi
else
  echo "Skipping log group creation (disabled or aws CLI not present)"
fi

# Restart application service if present (idempotent)
if command -v systemctl >/dev/null 2>&1; then
  if systemctl list-units --type=service --all | grep -q "${SERVICE_NAME}"; then
    echo "Restarting ${SERVICE_NAME} service (if running)"
    $SUDO systemctl restart ${SERVICE_NAME} || echo "Failed to restart ${SERVICE_NAME} (continuing)"
  fi
fi

echo "=== Deploy script finished at $(date -u) ==="