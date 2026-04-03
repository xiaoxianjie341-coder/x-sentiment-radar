from __future__ import annotations

from twitter_ops_agent.v2.contracts import TopicWorkspaceItem


def render_radar_note(*, day_key: str, items: list[TopicWorkspaceItem]) -> str:
    header = f"# {day_key} 今日雷达\n\n"
    if not items:
        return header + "今天没有新增主题，保留上一轮可看的结果即可。\n"
    sections: list[str] = []
    for label in ("中文版", "英文版"):
        bucket_items = [item for item in items if _resolve_language_version(item) == label]
        if not bucket_items:
            continue
        sections.append(f"## {label}")
        sections.append("")
        sections.extend(_render_item_block(item) for item in bucket_items)
        sections.append("")

    remaining = [item for item in items if _resolve_language_version(item) not in {"中文版", "英文版"}]
    if remaining:
        sections.append("## 其他")
        sections.append("")
        sections.extend(_render_item_block(item) for item in remaining)
        sections.append("")

    return header + "\n\n".join(section.rstrip() for section in sections if section is not None).rstrip() + "\n"


def _render_item_block(item: TopicWorkspaceItem) -> str:
    return "\n".join(
        [
            f"### {item.title}",
            f"- 赛道：{item.track or '综合'}",
            f"- 原推文：{item.source_url}",
            f"- 当前主情绪：{item.dominant_emotion}",
            f"- 主要分歧：{item.primary_tension}",
            f"- [[01_主题参考/{item.note_stem}]]",
            f"- [[02_可借用观点/{item.note_stem}]]",
        ]
    )


def _resolve_language_version(item: TopicWorkspaceItem) -> str:
    if item.language_version:
        return item.language_version
    sample = f"{item.title}\n{item.seed_text}"
    return "中文版" if _contains_cjk(sample) else "英文版"


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)
