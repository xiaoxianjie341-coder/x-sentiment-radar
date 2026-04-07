#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$ROOT_DIR"
PYTHONPATH=src python3 - <<'PY'
from twitter_ops_agent.config import load_settings, resolve_config_path
from twitter_ops_agent.discovery.polymarket import PolymarketSignalScout
from twitter_ops_agent.v2.cross_signal import CrossSignalStateStore

settings = load_settings(config_path=resolve_config_path(None), env={})
scout = PolymarketSignalScout(
    candidate_limit=settings.cross_signal_candidate_limit,
    filter_candidates=settings.cross_signal_filter_candidates,
)
candidates = scout.run()
store = CrossSignalStateStore(settings.cross_signal_state_file)
store.save_seen(tuple(candidate.slug for candidate in candidates if candidate.slug))
print(f"Primed state with {len(candidates)} Breaking candidates.")
print(settings.cross_signal_state_file)
PY
