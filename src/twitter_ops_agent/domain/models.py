from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class Account:
    account_id: str
    platform: str
    handle: str
    display_name: str | None = None


@dataclass(slots=True)
class Post:
    post_id: str
    account_id: str
    url: str
    created_at: datetime
    captured_at: datetime
    text_exact: str
    text_normalized: str
    post_type: str
    track: str | None = None
    conversation_id: str | None = None
    lang: str | None = None
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    views: int = 0


@dataclass(slots=True)
class PostRelation:
    relation_id: str
    from_post_id: str
    to_post_id: str
    relation_type: str
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class Event:
    event_id: str
    title: str | None = None
    track: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class EventPost:
    event_id: str
    post_id: str
    role_in_event: str
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class StyleExample:
    example_id: str
    handle: str
    track: str | None
    target_post_id: str
    target_text: str
    target_post_type: str
    target_url: str
    source_post_id: str | None
    source_text: str | None
    source_url: str | None
    source_kind: str


@dataclass(slots=True)
class CaptureResult:
    target_account: Account
    target_post: Post
    source_account: Account | None = None
    source_post: Post | None = None
    relations: tuple[PostRelation, ...] = ()


@dataclass(slots=True)
class EventLink:
    event_id: str
    source_role: str
    target_role: str
    title: str | None = None
    track: str | None = None


@dataclass(slots=True)
class EventContext:
    posts: tuple[Post, ...] = ()
    events: tuple[Event, ...] = ()
    event_posts: tuple[EventPost, ...] = ()
    by_post_id: dict[str, str] = field(default_factory=dict)
    by_conversation_id: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class EventBundle:
    event: Event | None = None
    posts: tuple[Post, ...] = ()
    event_posts: tuple[EventPost, ...] = ()
    seed_post: Post | None = None
    related_posts: tuple[Post, ...] = ()
    search_query: str = ""
    web_results: tuple[dict[str, str], ...] = ()
    crowd_summary: CrowdSummary | None = None


@dataclass(slots=True)
class DiscoveredTweet:
    source_list_id: str
    tweet_id: str
    author: str
    text: str
    url: str


@dataclass(slots=True)
class DiscoveryBatch:
    new_items: tuple[DiscoveredTweet, ...]
    next_seen_state: str


@dataclass(slots=True)
class Candidate:
    event_id: str
    track: str | None
    source_tier: str
    views: int
    batch_view_median: float
    related_event: bool
    has_market_or_regulatory_signal: bool


@dataclass(slots=True)
class ScoredCandidate(Candidate):
    score: int
    is_high_priority: bool


@dataclass(slots=True)
class LinkedCapture:
    capture: CaptureResult
    event_link: EventLink
    candidate: Candidate


@dataclass(slots=True)
class ScoreBatch:
    all_items: tuple[ScoredCandidate, ...]
    high_priority: tuple[ScoredCandidate, ...]


@dataclass(slots=True)
class CrowdSignal:
    tweet_id: str
    author_handle: str
    author_name: str
    text: str
    url: str
    likes: int = 0
    replies: int = 0
    views: int = 0
    bookmarks: int = 0
    signal_score: float = 0.0
    source_type: str = "reply"


@dataclass(slots=True)
class CrossSignalPost:
    tweet_id: str
    author_handle: str
    text: str
    url: str
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    quotes: int = 0
    views: int = 0
    spread_score: float = 0.0


@dataclass(slots=True)
class CrossSignalCandidate:
    slug: str
    title: str
    market_url: str
    source_label: str
    category_slug: str = ""
    secondary_category_slug: str = ""
    volume_24h: float = 0.0
    liquidity: float = 0.0


@dataclass(slots=True)
class CrossSignalAlert:
    topic: str
    market_title: str
    market_url: str
    source_label: str
    queries: tuple[str, ...] = ()
    top_posts: tuple[CrossSignalPost, ...] = ()
    angle_summary: str = ""
    distinct_post_count: int = 0
    distinct_account_count: int = 0
    verification_passed: bool = False


@dataclass(slots=True)
class CrowdSummary:
    sentiment_summary: str
    key_points: tuple[str, ...] = ()
    suggested_angles: tuple[str, ...] = ()
    top_signals: tuple[CrowdSignal, ...] = ()
    source_label: str = "评论区"


@dataclass(slots=True)
class ResearchCard:
    event_id: str
    track: str | None
    event_title: str
    seed_news_post: str
    one_paragraph_summary: str
    timeline: tuple[str, ...]
    key_entities: tuple[str, ...]
    why_it_matters: str
    likely_implications: tuple[str, ...]
    source_links: tuple[str, ...]
    draft_angles: tuple[str, ...]
    crowd_sentiment_summary: str = ""
    crowd_key_points: tuple[str, ...] = ()
    crowd_suggested_angles: tuple[str, ...] = ()
    crowd_top_signals: tuple[CrowdSignal, ...] = ()
    crowd_source_label: str = "评论区"


@dataclass(slots=True)
class DraftTweet:
    draft_id: str
    track: str | None
    tweet_text: str
    reasoning_outline: str
    source_post_ids: tuple[str, ...]
    translation_text: str = ""
    writer_name: str | None = None
    writer_model: str | None = None
    generated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class WrittenCandidateBundle:
    research_note_path: Path
    draft_note_path: Path


@dataclass(slots=True)
class BatchReport:
    discovered_count: int
    high_priority_count: int
    written_count: int
    style_example_count: int
    loaded_style_tracks: tuple[str, ...]
    remaining_day_budget: int


@dataclass(slots=True)
class StyleProfile:
    dominant_track: str | None
    common_openers: tuple[str, ...]
    common_phrases: tuple[str, ...]
    avg_line_count: int
    avg_char_count: int
    prefers_short_hook: bool
    sample_count: int
