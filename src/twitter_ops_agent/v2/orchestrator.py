from __future__ import annotations

from dataclasses import dataclass

from twitter_ops_agent.v2.contracts import ScoutRunResult, V2RunReport


@dataclass(slots=True)
class V2Orchestrator:
    scout: object
    hydration: object
    priority_gate: object
    crowd_sense: object
    angle_synthesizer: object
    publisher: object
    snapshot_store: object | None = None

    def run(self, *, day_key: str, last_seen: str | None = None):
        scout_result = self.scout.fetch_since(last_seen=last_seen) if hasattr(self.scout, "fetch_since") else self.scout.run()
        seeds = scout_result.seeds if hasattr(scout_result, "seeds") else list(scout_result)
        previous_snapshots = {}
        if self.snapshot_store is not None:
            previous_snapshots = self.snapshot_store.load_latest_v2_seed_snapshots([seed.tweet_id for seed in seeds])
        hydrated = self.hydration.run(seeds)
        selected = self.priority_gate.run(hydrated, previous_snapshots=previous_snapshots)
        if self.snapshot_store is not None and seeds:
            self.snapshot_store.record_v2_seed_snapshots(
                [
                    {
                        "tweet_id": seed.tweet_id,
                        "captured_at": self._now(),
                        "source_kind": seed.source_kind,
                        "query": seed.query,
                        "track": seed.track,
                        "views": seed.views,
                        "likes": seed.likes,
                        "replies": seed.replies,
                    }
                    for seed in seeds
                ]
            )
        items = [
            self.angle_synthesizer.run(seed, self.crowd_sense.run(seed))
            for seed in selected
        ]
        paths = self.publisher.write(day_key=day_key, items=items)
        report = V2RunReport(
            discovered_count=len(seeds),
            selected_count=len(selected),
            radar_written=1 if paths.get("radar_path") else 0,
            topic_notes_written=len(paths.get("topic_paths", [])),
            viewpoint_notes_written=len(paths.get("viewpoint_paths", [])),
        )
        if isinstance(scout_result, ScoutRunResult):
            report.next_seen_state = scout_result.next_seen_state  # type: ignore[attr-defined]
        return report

    def _now(self):
        import datetime as _datetime

        return _datetime.datetime.now(_datetime.timezone.utc)
