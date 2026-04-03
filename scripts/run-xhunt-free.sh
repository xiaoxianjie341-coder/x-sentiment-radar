#!/usr/bin/env zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_PATH="${ROOT_DIR}/config/settings.toml"
PYTHONPATH_VALUE="${ROOT_DIR}/src"

if [[ ! -f "${CONFIG_PATH}" ]]; then
  echo "Missing config file: ${CONFIG_PATH}" >&2
  exit 1
fi

cd "${ROOT_DIR}"

echo "[1/2] doctor"
env PYTHONPATH="${PYTHONPATH_VALUE}" python3 -m twitter_ops_agent.cli --config "${CONFIG_PATH}" doctor --json

echo "[2/2] run-v2"
env PYTHONPATH="${PYTHONPATH_VALUE}" python3 -m twitter_ops_agent.cli --config "${CONFIG_PATH}" run-v2
