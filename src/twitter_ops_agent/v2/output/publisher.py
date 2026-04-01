from __future__ import annotations

from pathlib import Path

from twitter_ops_agent.v2.contracts import TopicWorkspaceItem
from twitter_ops_agent.v2.output.borrowable_viewpoints_note import render_borrowable_viewpoints_note
from twitter_ops_agent.v2.output.radar_note import render_radar_note
from twitter_ops_agent.v2.output.topic_reference_note import render_topic_reference_note


class TopicWorkspacePublisher:
    def __init__(self, obsidian_root: Path) -> None:
        self.obsidian_root = obsidian_root

    def write(self, *, day_key: str, items: list[TopicWorkspaceItem]) -> dict[str, object]:
        radar_dir = self.obsidian_root / "00_今日雷达"
        topic_dir = self.obsidian_root / "01_主题参考"
        viewpoints_dir = self.obsidian_root / "02_可借用观点"
        processed_dir = self.obsidian_root / "03_处理记录"
        for directory in (radar_dir, topic_dir, viewpoints_dir, processed_dir):
            directory.mkdir(parents=True, exist_ok=True)

        radar_path = radar_dir / f"{day_key} 今日雷达.md"
        if items or not radar_path.exists():
            radar_path.write_text(render_radar_note(day_key=day_key, items=items), encoding="utf-8")

        topic_paths: list[str] = []
        viewpoint_paths: list[str] = []
        for item in items:
            topic_path = topic_dir / f"{item.note_stem}.md"
            viewpoint_path = viewpoints_dir / f"{item.note_stem}.md"
            topic_path.write_text(render_topic_reference_note(item), encoding="utf-8")
            viewpoint_path.write_text(render_borrowable_viewpoints_note(item), encoding="utf-8")
            topic_paths.append(str(topic_path))
            viewpoint_paths.append(str(viewpoint_path))

        return {
            "radar_path": str(radar_path),
            "topic_paths": topic_paths,
            "viewpoint_paths": viewpoint_paths,
        }
