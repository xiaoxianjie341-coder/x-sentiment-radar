from __future__ import annotations

from twitter_ops_agent.v2.contracts import TopicWorkspaceItem


def render_radar_note(*, day_key: str, items: list[TopicWorkspaceItem]) -> str:
    header = f"# {day_key} 今日雷达\n\n"
    if not items:
        return header + "今天没有新增主题，保留上一轮可看的结果即可。\n"
    blocks: list[str] = []
    for item in items:
        blocks.append(
            "\n".join(
                [
                    f"## {item.title}",
                    f"- 赛道：{item.track or '综合'}",
                    f"- 原推文：{item.source_url}",
                    f"- 当前主情绪：{item.dominant_emotion}",
                    f"- 主要分歧：{item.primary_tension}",
                    f"- [[01_主题参考/{item.note_stem}]]",
                    f"- [[02_可借用观点/{item.note_stem}]]",
                ]
            )
        )
    return header + "\n\n".join(blocks) + "\n"
