#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$ROOT_DIR/data/cross-signal"
OUT_FILE="$OUT_DIR/latest.json"

mkdir -p "$OUT_DIR"

cd "$ROOT_DIR"
PYTHONPATH=src python3 -m twitter_ops_agent.cli cross-signal --save-to "$OUT_FILE"

echo
echo "Saved report to:"
echo "$OUT_FILE"
