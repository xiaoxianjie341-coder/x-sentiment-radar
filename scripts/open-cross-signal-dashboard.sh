#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${1:-8765}"
PID_FILE="$ROOT_DIR/data/cross-signal/dashboard.pid"
LOG_FILE="$ROOT_DIR/data/cross-signal/dashboard.log"
URL="http://127.0.0.1:${PORT}/frontend/"

mkdir -p "$ROOT_DIR/data/cross-signal"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Dashboard server already running:"
  echo "$URL"
  open "$URL" >/dev/null 2>&1 || true
  exit 0
fi

cd "$ROOT_DIR"
nohup python3 -m http.server "$PORT" >"$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
sleep 1
open "$URL" >/dev/null 2>&1 || true
echo "$URL"
