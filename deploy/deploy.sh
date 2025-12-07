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

# Create CloudWatch agent configuration (write to agent's expected path)
CW_CONFIG_PATH="/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json"
echo "Creating CloudWatch agent config at $CW_CONFIG_PATH"
sudo mkdir -p "$(dirname "$CW_CONFIG_PATH")"

# Ensure common log directories and the application log exist and are writable
sudo mkdir -p /var/log/nginx || true
sudo mkdir -p /var/www/myapp || true
sudo touch /var/log/nginx/error.log /var/log/nginx/access.log /var/www/myapp/app.log /var/log/phase2.log || true
sudo chmod 666 /var/log/nginx/error.log /var/log/nginx/access.log /var/www/myapp/app.log /var/log/phase2.log || true

sudo tee "$CW_CONFIG_PATH" > /dev/null <<'CWCONFIG'
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/syslog",
            "log_group_name": "ec2-syslog",
            "log_stream_name": "{instance_id}",
            "create_log_group": true
          },
          {
            "file_path": "/var/log/nginx/error.log",
            "log_group_name": "nginx-error",
            "log_stream_name": "{instance_id}",
            "create_log_group": true
          },
          {
            "file_path": "/var/log/nginx/access.log",
            "log_group_name": "nginx-access",
            "log_stream_name": "{instance_id}",
            "create_log_group": true
          },
          {
            "file_path": "/var/www/myapp/app.log",
            "log_group_name": "app-log",
            "log_stream_name": "{instance_id}",
            "create_log_group": true
          },
          {
            "file_path": "/var/log/phase2.log",
            "log_group_name": "phase2-app",
            "log_stream_name": "{instance_id}",
            "create_log_group": true
          }
        ]
      }
    }
  }
}
CWCONFIG

# Optionally create CloudWatch Log Groups (useful when deploying to a fresh account).
# Set environment variable `CREATE_LOG_GROUP=false` to skip group creation.
CREATE_LOG_GROUP=${CREATE_LOG_GROUP:-true}
# Default retention in days (set via LOG_RETENTION_DAYS env var)
LOG_RETENTION_DAYS=${LOG_RETENTION_DAYS:-14}

# Start or reload CloudWatch Agent using the ctl helper if available (ensures it picks up the file:// config), otherwise fall back to systemctl
if /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl --help >/dev/null 2>&1; then
  echo "Loading CloudWatch agent config with amazon-cloudwatch-agent-ctl"
  sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config -m ec2 -c file:$CW_CONFIG_PATH -s || true
else
  echo "amazon-cloudwatch-agent-ctl not found; using systemctl to restart agent"
  sudo systemctl enable amazon-cloudwatch-agent || true
  sudo systemctl restart amazon-cloudwatch-agent || true
fi

echo "[CloudWatch] CloudWatch Agent setup complete."

# Create CloudWatch log groups if requested (requires aws CLI and appropriate IAM role)
if [ "$CREATE_LOG_GROUP" = "true" ]; then
  if command -v aws >/dev/null 2>&1; then
    echo "Creating CloudWatch log groups (if missing) with retention ${LOG_RETENTION_DAYS} days..."
    AWS_REGION=${AWS_REGION:-us-east-2}
    # list of groups to ensure exist
    LOG_GROUPS=("ec2-syslog" "nginx-error" "nginx-access" "app-log" "phase2-app")
    for lg in "${LOG_GROUPS[@]}"; do
      # check if log group exists
      if aws logs describe-log-groups --log-group-name-prefix "$lg" --region "$AWS_REGION" --no-cli-pager | grep -q 'logGroupName'; then
        echo "Log group $lg already exists (or similar). Ensuring retention..."
        aws logs put-retention-policy --log-group-name "$lg" --retention-in-days "$LOG_RETENTION_DAYS" --region "$AWS_REGION" || true
      else
        echo "Creating log group $lg"
        aws logs create-log-group --log-group-name "$lg" --region "$AWS_REGION" || true
        aws logs put-retention-policy --log-group-name "$lg" --retention-in-days "$LOG_RETENTION_DAYS" --region "$AWS_REGION" || true
      fi
    done
  else
    echo "aws CLI not found; skipping CloudWatch log group creation."
  fi
fi
