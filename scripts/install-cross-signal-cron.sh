#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT_DIR/data/cross-signal"
LOG_FILE="$LOG_DIR/cron.log"
TAG="# x-sentiment-radar cross-signal"

mkdir -p "$LOG_DIR"

echo "Priming current Breaking candidates into seen state..."
"$ROOT_DIR/scripts/prime-cross-signal-state.sh" >/dev/null

CRON_CMD="*/30 * * * * cd $ROOT_DIR && ./scripts/run-cross-signal-grok.sh >> $LOG_FILE 2>&1 $TAG"

TMP_CRON="$(mktemp)"
crontab -l 2>/dev/null | grep -v "$TAG" > "$TMP_CRON" || true
echo "$CRON_CMD" >> "$TMP_CRON"
crontab "$TMP_CRON"
rm -f "$TMP_CRON"

echo "Installed cron job:"
echo "$CRON_CMD"
echo
echo "Logs:"
echo "$LOG_FILE"
