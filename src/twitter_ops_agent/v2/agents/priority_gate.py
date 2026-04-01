from __future__ import annotations

from dataclasses import dataclass

from twitter_ops_agent.v2.contracts import HydratedSeed


@dataclass(slots=True)
class PriorityGateAgent:
    daily_budget: int = 10

    def run(self, hydrated: list[HydratedSeed], previous_snapshots: dict[str, dict[str, object]] | None = None) -> list[HydratedSeed]:
        snapshots = previous_snapshots or {}
        ranked = sorted(hydrated, key=lambda item: self._score(item, snapshots.get(item.seed.tweet_id)), reverse=True)
        return ranked[: self.daily_budget]

    def _score(self, item: HydratedSeed, previous_snapshot: dict[str, object] | None) -> float:
        seed = item.seed
        track_bonus = 100 if seed.track in {"AI", "Crypto"} else 0
        delta_views = max(seed.views - int(previous_snapshot.get("views", 0)), 0) if previous_snapshot else 0
        delta_replies = max(seed.replies - int(previous_snapshot.get("replies", 0)), 0) if previous_snapshot else 0
        delta_likes = max(seed.likes - int(previous_snapshot.get("likes", 0)), 0) if previous_snapshot else 0
        return (
            track_bonus
            + seed.velocity_hint * 10
            + delta_replies * 20
            + delta_likes * 5
            + min(delta_views / 200.0, 200.0)
            + seed.replies * 4
            + seed.likes * 1.5
            + min(seed.views / 5000.0, 50.0)
        )
