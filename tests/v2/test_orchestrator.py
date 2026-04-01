from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from twitter_ops_agent.domain.models import CrowdSummary
from twitter_ops_agent.v2.contracts import ScoutSeed, TopicWorkspaceItem
from twitter_ops_agent.v2.orchestrator import V2Orchestrator


@dataclass
class StubScout:
    def run(self):
        return [
            ScoutSeed(
                seed_id="seed-1",
                source_kind="tweet",
                query="anthropic",
                tweet_id="tweet-1",
                url="https://x.com/example/status/1",
                text="Anthropic accidentally shipped internal source maps.",
                title="Anthropic Source Leak",
                track="AI",
                author_handle="anthropicnews",
                views=10000,
                replies=100,
                likes=300,
                velocity_hint=200.0,
            )
        ]


@dataclass
class StubHydration:
    def run(self, seeds):
        return seeds


@dataclass
class StubGate:
    def run(self, seeds, previous_snapshots=None):
        return seeds


@dataclass
class StubCrowdSense:
    def run(self, seed):
        return CrowdSummary(
            sentiment_summary="评论区偏质疑。",
            key_points=("很多人关心这是不是事故。",),
            suggested_angles=("可以从信任危机切。",),
            top_signals=(),
            source_label="评论区",
        )


@dataclass
class StubAngle:
    def run(self, seed, crowd_summary):
        return TopicWorkspaceItem(
            event_id="event-1",
            note_stem="2026-04-01 [AI] Anthropic Source Leak",
            track="AI",
            title="Anthropic Source Leak",
            source_kind="tweet",
            source_url=seed.url,
            source_author_handle=seed.author_handle,
            seed_text=seed.text,
            why_now="The topic is accelerating.",
            dominant_emotion="质疑",
            primary_tension="事故还是营销。",
            crowd_summary=crowd_summary,
            research_directions=("先验证事实，再看信任层影响。",),
            borrowable_viewpoints=("真正值得写的是信任问题。",),
            created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        )


@dataclass
class StubPublisher:
    def write(self, *, day_key, items):
        return {
            "radar_path": "/tmp/radar.md",
            "topic_paths": ["/tmp/topic.md"],
            "viewpoint_paths": ["/tmp/viewpoints.md"],
        }


@dataclass
class StubSnapshotStore:
    loaded_ids: list[str] | None = None
    recorded: list[dict[str, object]] | None = None

    def load_latest_v2_seed_snapshots(self, tweet_ids):
        self.loaded_ids = list(tweet_ids)
        return {"tweet-1": {"views": 5000, "likes": 100, "replies": 30}}

    def record_v2_seed_snapshots(self, snapshots):
        self.recorded = list(snapshots)


def test_v2_orchestrator_runs_end_to_end():
    snapshot_store = StubSnapshotStore()
    orchestrator = V2Orchestrator(
        scout=StubScout(),
        hydration=StubHydration(),
        priority_gate=StubGate(),
        crowd_sense=StubCrowdSense(),
        angle_synthesizer=StubAngle(),
        publisher=StubPublisher(),
        snapshot_store=snapshot_store,
    )

    report = orchestrator.run(day_key="2026-04-01")

    assert report.discovered_count == 1
    assert report.selected_count == 1
    assert report.radar_written == 1
    assert report.topic_notes_written == 1
    assert report.viewpoint_notes_written == 1
    assert snapshot_store.loaded_ids == ["tweet-1"]
    assert snapshot_store.recorded is not None
