from __future__ import annotations

from datetime import datetime, timezone

from twitter_ops_agent.domain.models import CrowdSignal, CrowdSummary
from twitter_ops_agent.v2.contracts import TopicWorkspaceItem
from twitter_ops_agent.v2.output.borrowable_viewpoints_note import render_borrowable_viewpoints_note
from twitter_ops_agent.v2.output.radar_note import render_radar_note
from twitter_ops_agent.v2.output.topic_reference_note import render_topic_reference_note


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
        why_now="The topic is accelerating and replies are forming a clear argument about trust and distribution.",
        dominant_emotion="质疑",
        primary_tension="大家在争这是事故、营销，还是能力泄露。",
        crowd_summary=CrowdSummary(
            sentiment_summary="评论区整体偏质疑，核心争论在于这到底是失误还是展示真实工程能力。",
            key_points=("很多人质疑这是不是刻意放出来的。", "也有人觉得真正重点是开发者对 Claude Code 内部实现的兴趣。"),
            suggested_angles=("可以从『失误』和『工程能力暴露』的张力切入。",),
            top_signals=(
                CrowdSignal(
                    tweet_id="reply-1",
                    author_handle="builder01",
                    author_name="Builder",
                    text="The real story is not the leak. It's that devs want to see how these tools are actually built.",
                    url="https://x.com/builder01/status/1",
                    likes=88,
                    replies=12,
                    views=5000,
                    bookmarks=9,
                    signal_score=99.0,
                    source_type="reply",
                ),
            ),
            source_label="评论区",
        ),
        research_directions=(
            "继续验证这是单纯事故，还是团队发布链路有系统性问题。",
            "继续找开发者为什么对内部实现这么感兴趣。",
        ),
        borrowable_viewpoints=(
            "真正值得写的不是泄露本身，而是开发者为什么这么渴望看到 AI 工具的内部实现。",
            "如果评论区一直在讨论可信度，那就说明『信任』已经成了这个话题的主战场。",
        ),
        created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )


def test_render_topic_reference_note_contains_zero_learning_cost_sections():
    note = render_topic_reference_note(_item())

    assert "## 这个主题是什么" in note
    assert "## 现在大家在聊什么" in note
    assert "## 当前主情绪" in note
    assert "## 主要分歧点" in note
    assert "## 高质量评论" in note
    assert "## 可继续研究的方向" in note
    assert "[[02_可借用观点/" in note


def test_render_borrowable_viewpoints_note_contains_cross_reference_material():
    note = render_borrowable_viewpoints_note(_item())

    assert "## 最值得借的观点" in note
    assert "## 可交叉引用评论" in note
    assert "## 可以继续展开的方向" in note
    assert "[[01_主题参考/" in note


def test_render_radar_note_links_to_topic_and_viewpoints():
    note = render_radar_note(day_key="2026-04-01", items=[_item()])

    assert "# 2026-04-01 今日雷达" in note
    assert "Anthropic Source Leak" in note
    assert "https://x.com/example/status/1" in note
    assert "[[01_主题参考/2026-04-01 [AI] Anthropic Source Leak]]" in note
    assert "[[02_可借用观点/2026-04-01 [AI] Anthropic Source Leak]]" in note
