from __future__ import annotations

from twitter_ops_agent.v2.contracts import TopicWorkspaceItem

MAX_RENDERED_SIGNALS = 10


def render_borrowable_viewpoints_note(item: TopicWorkspaceItem) -> str:
    return f"""# {item.title}

## 最值得借的观点
{_render_lines(item.borrowable_viewpoints)}

## 可交叉引用评论
{_render_top_signals(item)}

## 可以继续展开的方向
{_render_lines(item.research_directions)}

## 跳转
- [[01_主题参考/{item.note_stem}]]
- [[00_今日雷达/{item.created_at.date().isoformat()} 今日雷达]]
"""


def _render_top_signals(item: TopicWorkspaceItem) -> str:
    if not item.crowd_summary.top_signals:
        return "- 暂无\n"
    return "".join(
        f"- @{signal.author_handle}：{signal.text}\n  {signal.url}\n"
        for signal in item.crowd_summary.top_signals[:MAX_RENDERED_SIGNALS]
    )


def _render_lines(values: tuple[str, ...]) -> str:
    if not values:
        return "- 暂无\n"
    return "".join(f"- {value}\n" for value in values)
