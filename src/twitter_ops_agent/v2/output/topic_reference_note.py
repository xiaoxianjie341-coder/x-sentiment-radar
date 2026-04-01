from __future__ import annotations

from twitter_ops_agent.v2.contracts import TopicWorkspaceItem


def render_topic_reference_note(item: TopicWorkspaceItem) -> str:
    return f"""# {item.title}

## 这个主题是什么
{item.seed_text}

## 原始内容
- 来源类型：{item.source_kind}
- 原帖作者：@{item.source_author_handle}
- 原帖链接：{item.source_url}

## 现在大家在聊什么
{item.why_now}

## 当前主情绪
{item.dominant_emotion}

## 主要分歧点
{item.primary_tension}

## 高质量评论
{_render_top_signals(item)}

## 可继续研究的方向
{_render_lines(item.research_directions)}

## 跳转
- [[00_今日雷达/{item.created_at.date().isoformat()} 今日雷达]]
- [[02_可借用观点/{item.note_stem}]]
"""


def _render_top_signals(item: TopicWorkspaceItem) -> str:
    if not item.crowd_summary.top_signals:
        return "- 暂无稳定高信号评论\n"
    lines: list[str] = []
    for index, signal in enumerate(item.crowd_summary.top_signals[:5], start=1):
        lines.append(
            f"- {index}. @{signal.author_handle} | 赞 {signal.likes} | 回 {signal.replies} | 浏览 {signal.views}\n"
            f"  {signal.text}\n"
            f"  {signal.url}"
        )
    return "\n".join(lines) + "\n"


def _render_lines(values: tuple[str, ...]) -> str:
    if not values:
        return "- 暂无\n"
    return "".join(f"- {value}\n" for value in values)
