from __future__ import annotations

from datetime import datetime, timezone

from twitter_ops_agent.domain.models import CrowdSummary
from twitter_ops_agent.v2.contracts import TopicWorkspaceItem
from twitter_ops_agent.v2.output.publisher import TopicWorkspacePublisher


def _item() -> TopicWorkspaceItem:
    return TopicWorkspaceItem(
        event_id="event-1",
        note_stem="2026-04-01 [AI] Anthropic Source Leak",
        track="AI",
        title="Anthropic Source Leak",
        source_kind="tweet",
        source_url="https://x.com/example/status/1",
        source_author_handle="anthropicnews",
        seed_text="Anthropic accidentally shipped internal source maps.",
        why_now="The topic is accelerating.",
        dominant_emotion="质疑",
        primary_tension="事故还是营销。",
        crowd_summary=CrowdSummary(sentiment_summary="评论区偏质疑。"),
        research_directions=("先确认是不是失误。",),
        borrowable_viewpoints=("真正值得写的是信任问题。",),
        created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )


def test_publisher_keeps_existing_radar_when_new_run_has_no_items(tmp_path):
    publisher = TopicWorkspacePublisher(tmp_path)
    publisher.write(day_key="2026-04-01", items=[_item()])

    radar_path = tmp_path / "00_今日雷达" / "2026-04-01 今日雷达.md"
    first = radar_path.read_text(encoding="utf-8")

    publisher.write(day_key="2026-04-01", items=[])
    second = radar_path.read_text(encoding="utf-8")

    assert first == second
