#!/usr/bin/env bash
# Installs (or updates) the Teacher Planner server on an Ubuntu machine and
# runs it as a background service that starts on boot.
#
#   curl -fsSL https://raw.githubusercontent.com/K1llerqueenz/TeacherPlanner/main/server/install-ubuntu.sh | sudo bash
#
# Run it again any time to pull the latest code and restart the server.
# Change the port with: sudo PLANNER_PORT=8050 bash install-ubuntu.sh
set -euo pipefail

PORT="${PLANNER_PORT:-8040}"
REPO_URL="https://github.com/K1llerqueenz/TeacherPlanner.git"
BRANCH="${PLANNER_BRANCH:-main}"
APP_DIR=/opt/teacherplanner
DATA_DIR=/var/lib/teacherplanner
SERVICE=teacherplanner

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run with sudo." >&2
  exit 1
fi

echo "==> Installing system packages"
apt-get update -qq
apt-get install -y -qq git python3 python3-venv >/dev/null

if ! id teacherplanner >/dev/null 2>&1; then
  useradd --system --home "$DATA_DIR" --shell /usr/sbin/nologin teacherplanner
fi
mkdir -p "$DATA_DIR"
chown teacherplanner:teacherplanner "$DATA_DIR"

echo "==> Getting the latest code"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" fetch -q origin "$BRANCH"
  git -C "$APP_DIR" checkout -q "$BRANCH"
  git -C "$APP_DIR" reset -q --hard "origin/$BRANCH"
else
  git clone -q --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

echo "==> Installing Python packages"
python3 -m venv "$APP_DIR/server/.venv"
"$APP_DIR/server/.venv/bin/pip" install -q --upgrade pip
"$APP_DIR/server/.venv/bin/pip" install -q -r "$APP_DIR/server/requirements.txt"

echo "==> Setting up the background service on port $PORT"
cat > /etc/systemd/system/$SERVICE.service <<UNIT
[Unit]
Description=Teacher Planner server
After=network-online.target
Wants=network-online.target

[Service]
User=teacherplanner
WorkingDirectory=$APP_DIR/server
Environment=PLANNER_DB_PATH=$DATA_DIR/planner.db
ExecStart=$APP_DIR/server/.venv/bin/uvicorn app:app --host 0.0.0.0 --port $PORT --workers 1 --proxy-headers
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable -q $SERVICE
systemctl restart $SERVICE

if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
  ufw allow "$PORT/tcp" >/dev/null
  echo "==> Opened port $PORT in the firewall"
fi

sleep 2
if curl -fsS "http://127.0.0.1:$PORT/docs" >/dev/null; then
  echo
  echo "Teacher Planner server is running."
  echo "Address for the app: http://$(hostname -I | awk '{print $1}'):$PORT"
else
  echo "The server did not start. See: sudo journalctl -u $SERVICE -n 50" >&2
  exit 1
fi
