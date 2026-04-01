from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from twitter_ops_agent.domain.models import CrowdSummary


@dataclass(slots=True)
class ScoutSeed:
    seed_id: str
    source_kind: str
    query: str
    tweet_id: str
    url: str
    text: str
    title: str
    track: str | None
    author_handle: str
    views: int = 0
    replies: int = 0
    likes: int = 0
    velocity_hint: float = 0.0


@dataclass(slots=True)
class ScoutRunResult:
    seeds: list[ScoutSeed]
    next_seen_state: str


@dataclass(slots=True)
class TopicWorkspaceItem:
    event_id: str
    note_stem: str
    track: str | None
    title: str
    source_kind: str
    source_url: str
    source_author_handle: str
    seed_text: str
    why_now: str
    dominant_emotion: str
    primary_tension: str
    crowd_summary: CrowdSummary
    research_directions: tuple[str, ...] = ()
    borrowable_viewpoints: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class HydratedSeed:
    seed: ScoutSeed
    event_id: str
    source_url: str
    source_text: str
    track: str | None


@dataclass(slots=True)
class V2RunReport:
    discovered_count: int
    selected_count: int
    radar_written: int
    topic_notes_written: int
    viewpoint_notes_written: int
    next_seen_state: str = ""
