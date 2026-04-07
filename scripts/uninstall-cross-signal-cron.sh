#!/usr/bin/env bash
set -euo pipefail

TAG="# x-sentiment-radar cross-signal"
TMP_CRON="$(mktemp)"

crontab -l 2>/dev/null | grep -v "$TAG" > "$TMP_CRON" || true
crontab "$TMP_CRON"
rm -f "$TMP_CRON"

echo "Removed cross-signal cron job."
