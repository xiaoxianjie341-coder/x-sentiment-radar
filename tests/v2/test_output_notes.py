from __future__ import annotations

from datetime import datetime, timezone

from twitter_ops_agent.domain.models import CrowdSignal, CrowdSummary
from twitter_ops_agent.v2.contracts import TopicWorkspaceItem
from twitter_ops_agent.v2.output.borrowable_viewpoints_note import render_borrowable_viewpoints_note
from twitter_ops_agent.v2.output.radar_note import render_radar_note
from twitter_ops_agent.v2.output.topic_reference_note import render_topic_reference_note


def _signal(index: int, text: str, *, likes: int = 0, replies: int = 0, views: int = 0) -> CrowdSignal:
    return CrowdSignal(
        tweet_id=f"reply-{index}",
        author_handle=f"user{index}",
        author_name=f"User {index}",
        text=text,
        url=f"https://x.com/user{index}/status/{index}",
        likes=likes,
        replies=replies,
        views=views,
        bookmarks=index,
        signal_score=float(100 - index),
        source_type="reply",
    )


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
                _signal(1, "This feels fake and people should ask for better evidence before trusting the launch story.", likes=88, replies=12, views=5000),
                _signal(2, "Huge risk if the team keeps moving fast without fixing the trust gap that this thread exposed.", likes=21, replies=4, views=4200),
                _signal(3, "The upside is obvious if they execute, because dev workflows will compound around whatever tools earn trust first.", likes=65, replies=10, views=6100),
                _signal(4, "I mostly want the factual timeline, because the comments are mixing product criticism with speculation.", likes=4, replies=0, views=1300),
                _signal(5, "This feels fake and people should ask for better evidence before trusting the launch story again with real numbers.", likes=17, replies=3, views=3500),
                _signal(6, "The upside is obvious if they execute, because developers still want a reliable workflow more than hype.", likes=19, replies=2, views=2600),
                _signal(7, "Huge risk if community trust keeps slipping while the roadmap gets pushed again and again.", likes=8, replies=1, views=1700),
                _signal(8, "I mostly want a clean explanation of what actually shipped, who it helps, and what changed this week.", likes=1, replies=0, views=900),
                _signal(9, "This feels fake because the launch message is confident but the evidence in the thread is still thin.", likes=5, replies=1, views=1400),
                _signal(10, "The upside is obvious if they can convert curiosity into actual product retention over the next month.", likes=6, replies=0, views=1100),
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
    assert "## 情绪分布" in note
    assert "## 主要分歧点" in note
    assert "## 高质量评论" in note
    assert "## 按情绪分类看评论" in note
    assert "### 质疑/求证" in note
    assert "### 担忧/风险" in note
    assert "### 兴奋/机会" in note
    assert "### 中性/信息补充" in note
    assert "https://x.com/user10/status/10" in note
    assert "## 可继续研究的方向" in note
    assert "[[02_可借用观点/" in note


def test_render_borrowable_viewpoints_note_contains_cross_reference_material():
    note = render_borrowable_viewpoints_note(_item())

    assert "## 最值得借的观点" in note
    assert "## 可交叉引用评论" in note
    assert "https://x.com/user10/status/10" in note
    assert "## 可以继续展开的方向" in note
    assert "[[01_主题参考/" in note


def test_render_radar_note_links_to_topic_and_viewpoints():
    note = render_radar_note(day_key="2026-04-01", items=[_item()])

    assert "# 2026-04-01 今日雷达" in note
    assert "Anthropic Source Leak" in note
    assert "https://x.com/example/status/1" in note
    assert "[[01_主题参考/2026-04-01 [AI] Anthropic Source Leak]]" in note
    assert "[[02_可借用观点/2026-04-01 [AI] Anthropic Source Leak]]" in note


def test_render_topic_reference_note_compacts_multiline_signal_text_for_readability():
    item = _item()
    item.crowd_summary.top_signals = (
        _signal(
            99,
            "@Murphychen888 同意以下6点：\n1.CVDD 是少数长期有效的指标\n2.当前策略：等待 + 轻仓\n3.底部区域：$45,000-55,000",
            likes=8,
            replies=1,
            views=1800,
        ),
    )

    note = render_topic_reference_note(item)

    assert "@Murphychen888 同意以下6点" not in note
    assert "当前策略：等待 + 轻仓" in note
    assert "1.CVDD 是少数长期有效的指标" not in note
