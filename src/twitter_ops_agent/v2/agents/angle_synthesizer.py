from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re

from twitter_ops_agent.domain.models import CrowdSummary
from twitter_ops_agent.v2.contracts import HydratedSeed, TopicWorkspaceItem


@dataclass(slots=True)
class AngleSynthesizerAgent:
    day_key: str

    def run(self, seed: HydratedSeed, crowd_summary: CrowdSummary) -> TopicWorkspaceItem:
        title = _build_title(seed.seed.title or seed.source_text)
        note_stem = f"{self.day_key} [{seed.track or '综合'}] {title}"
        why_now = _build_why_now(seed)
        primary_tension = _build_primary_tension(crowd_summary)
        research_directions = _build_research_directions(crowd_summary, seed)
        borrowable_viewpoints = _build_borrowable_viewpoints(crowd_summary)
        return TopicWorkspaceItem(
            event_id=seed.event_id,
            note_stem=note_stem,
            track=seed.track,
            title=title,
            source_kind=seed.seed.source_kind,
            source_url=seed.source_url,
            source_author_handle=seed.seed.author_handle,
            seed_text=seed.source_text,
            why_now=why_now,
            dominant_emotion=_infer_emotion_label(crowd_summary.sentiment_summary),
            primary_tension=primary_tension,
            crowd_summary=crowd_summary,
            research_directions=research_directions,
            borrowable_viewpoints=borrowable_viewpoints,
            created_at=datetime.fromisoformat(self.day_key).replace(tzinfo=timezone.utc),
        )


def _build_title(text: str) -> str:
    compact = " ".join(text.split())
    compact = re.sub(r"[\\/:*?\"<>|]", " ", compact).strip()
    return compact[:80] or "未命名主题"


def _build_why_now(seed: HydratedSeed) -> str:
    return (
        f"这条内容当前已经有 {seed.seed.views} 浏览、{seed.seed.replies} 条回复，"
        f"而且来自 {seed.seed.source_kind} 入口，说明它不只是被看到，而是已经开始形成讨论。"
    )


def _build_primary_tension(crowd_summary: CrowdSummary) -> str:
    if crowd_summary.key_points:
        return crowd_summary.key_points[0]
    return crowd_summary.sentiment_summary or "评论区暂时还没有形成稳定分歧。"


def _build_research_directions(crowd_summary: CrowdSummary, seed: HydratedSeed) -> tuple[str, ...]:
    directions = list(crowd_summary.key_points[:3])
    if not directions:
        directions.append("继续验证原帖里的核心信息是否已经被更多人引用或反驳。")
    directions.append(f"继续观察 @{seed.seed.author_handle} 下面的新回复，看看分歧会不会继续扩大。")
    return tuple(dict.fromkeys(directions))[:4]


def _build_borrowable_viewpoints(crowd_summary: CrowdSummary) -> tuple[str, ...]:
    points: list[str] = []
    for signal in crowd_summary.top_signals[:5]:
        text = " ".join(signal.text.split())
        points.append(text[:160] + ("..." if len(text) > 160 else ""))
    if not points and crowd_summary.key_points:
        points.extend(crowd_summary.key_points[:3])
    return tuple(points)


def _infer_emotion_label(sentiment_summary: str) -> str:
    if "质疑" in sentiment_summary or "求证" in sentiment_summary:
        return "质疑"
    if "风险" in sentiment_summary or "谨慎" in sentiment_summary:
        return "谨慎"
    if "兴奋" in sentiment_summary or "机会" in sentiment_summary:
        return "兴奋"
    if "分歧" in sentiment_summary:
        return "分裂"
    return "观察"
