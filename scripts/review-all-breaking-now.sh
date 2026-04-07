#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$ROOT_DIR/data/cross-signal"
OUT_FILE="$OUT_DIR/latest.json"

mkdir -p "$OUT_DIR"

cd "$ROOT_DIR"
PYTHONPATH=src python3 - <<'PY'
import json
from pathlib import Path

from twitter_ops_agent.cli import (
    _serialize_cross_signal_alert,
    _serialize_cross_signal_candidate,
    _serialize_cross_signal_review,
    build_grok_cross_signal_gate,
)
from twitter_ops_agent.config import load_settings, resolve_config_path
from twitter_ops_agent.discovery.polymarket import PolymarketSignalScout
from twitter_ops_agent.v2.cross_signal import _review_candidate, _to_candidate_preview
from twitter_ops_agent.domain.models import CrossSignalAlert

settings = load_settings(config_path=resolve_config_path(None), env={})
scout = PolymarketSignalScout(
    candidate_limit=settings.cross_signal_candidate_limit,
    filter_candidates=settings.cross_signal_filter_candidates,
)
gate = build_grok_cross_signal_gate(settings)
candidates = scout.run()

out = Path("data/cross-signal/latest.json")
out.parent.mkdir(parents=True, exist_ok=True)

reviews = []
alerts = []
candidate_payload = [_serialize_cross_signal_candidate(_to_candidate_preview(candidate)) for candidate in candidates]

def write_snapshot():
    payload = {
        "candidate_count": len(candidates),
        "new_candidate_count": len(candidates),
        "passed_count": len(alerts),
        "candidates": candidate_payload,
        "new_candidates": candidate_payload,
        "reviewed_candidates": [_serialize_cross_signal_review(review) for review in reviews],
        "topics": [_serialize_cross_signal_alert(alert) for alert in alerts],
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

write_snapshot()

for index, candidate in enumerate(candidates, start=1):
    review = _review_candidate(gate, candidate)
    reviews.append(review)
    if review.is_viral:
        alerts.append(
            CrossSignalAlert(
                topic=review.slug or review.market_title,
                market_title=review.market_title,
                market_url=review.market_url,
                source_label=review.source_label,
                queries=review.queries,
                top_posts=review.top_posts,
                angle_summary=review.angle_summary,
                distinct_post_count=review.distinct_post_count,
                distinct_account_count=review.distinct_account_count,
                verification_passed=True,
            )
        )
    write_snapshot()
    print(f"[{index}/{len(candidates)}] {candidate.slug} -> {'PASS' if review.is_viral else 'FAIL'}")

print(out)
print(f"candidate_count {len(candidates)}")
print(f"reviewed_candidates {len(reviews)}")
print(f"passed_count {len(alerts)}")
PY

echo
echo "Saved full review to:"
echo "$OUT_FILE"
