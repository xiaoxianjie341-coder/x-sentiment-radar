from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence
from zoneinfo import ZoneInfo

from twitter_ops_agent.config import load_settings, resolve_config_path
from twitter_ops_agent.discovery.attentionvc import AttentionVCArticleClient
from twitter_ops_agent.doctor import run_doctor
from twitter_ops_agent.events.linker import EventService
from twitter_ops_agent.research.crowd_context import CrowdContextService, LLMCrowdSummarizer
from twitter_ops_agent.storage.repository import SqliteRepository
from twitter_ops_agent.v2.agents.angle_synthesizer import AngleSynthesizerAgent
from twitter_ops_agent.v2.agents.crowd_sense import CrowdSenseAgent
from twitter_ops_agent.v2.agents.hydration_agent import HydrationAgent
from twitter_ops_agent.v2.agents.priority_gate import PriorityGateAgent
from twitter_ops_agent.v2.agents.topic_scout import TopicScoutAgent
from twitter_ops_agent.v2.orchestrator import V2Orchestrator
from twitter_ops_agent.v2.output.publisher import TopicWorkspacePublisher
from twitter_ops_agent.writer.llm_writer import LLMWriterConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="x-sentiment-radar")
    parser.add_argument("--config", type=Path, default=None, help="Path to a TOML settings file.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subcommands.add_parser("doctor", help="Inspect resolved settings and output paths.")
    doctor_parser.add_argument("--json", action="store_true", help="Emit the doctor report as JSON.")

    subcommands.add_parser("run-v2", help="Run the sentiment-first workflow.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = load_settings(config_path=resolve_config_path(args.config), env=os.environ)

    if args.command == "doctor":
        report = run_doctor(settings=settings, capture_service=None)
        if args.json:
            print(
                json.dumps(
                    {
                        "obsidian_root": str(report.obsidian_root),
                        "sqlite_db": str(report.sqlite_db),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(f"obsidian_root: {report.obsidian_root}")
            print(f"sqlite_db: {report.sqlite_db}")
        return 0

    if args.command == "run-v2":
        try:
            report = run_v2(settings=settings)
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
            return 1
        print(
            json.dumps(
                {
                    "discovered_count": report.discovered_count,
                    "selected_count": report.selected_count,
                    "radar_written": report.radar_written,
                    "topic_notes_written": report.topic_notes_written,
                    "viewpoint_notes_written": report.viewpoint_notes_written,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2


class SystemClock:
    def now(self):
        import datetime as _datetime

        return _datetime.datetime.now(_datetime.timezone.utc)


def run_v2(settings):
    repo = SqliteRepository(settings.sqlite_db)
    attention_client = build_attention_client(settings)
    if attention_client is None:
        raise RuntimeError("AttentionVC API key is required for run-v2.")

    orchestrator = V2Orchestrator(
        scout=TopicScoutAgent(
            client=attention_client,
            categories=settings.attentionvc_categories,
            article_window=settings.attentionvc_window,
            article_limit_per_category=settings.attentionvc_limit_per_category,
            use_rising_articles=settings.attentionvc_use_rising,
            rising_hours=settings.attentionvc_rising_hours,
            search_queries=settings.attentionvc_search_queries,
            search_limit_per_query=settings.attentionvc_search_limit_per_query,
            source_mode=settings.attentionvc_source_mode,
            seed_min_views=settings.attentionvc_seed_min_views,
            seed_min_likes=settings.attentionvc_seed_min_likes,
            seed_min_replies=settings.attentionvc_seed_min_replies,
            article_min_views=settings.attentionvc_article_min_views,
            article_min_likes=settings.attentionvc_article_min_likes,
            article_min_replies=settings.attentionvc_article_min_replies,
            tweet_min_views=settings.attentionvc_tweet_min_views,
            tweet_min_likes=settings.attentionvc_tweet_min_likes,
            tweet_min_replies=settings.attentionvc_tweet_min_replies,
        ),
        hydration=HydrationAgent(repo=repo, events=EventService(repo)),
        priority_gate=PriorityGateAgent(daily_budget=settings.daily_candidate_budget),
        crowd_sense=CrowdSenseAgent(
            crowd_context=build_crowd_context_service(settings, attention_client=attention_client),
            signal_min_views=settings.attentionvc_signal_min_views,
            signal_min_likes=settings.attentionvc_signal_min_likes,
            signal_min_replies=settings.attentionvc_signal_min_replies,
        ),
        angle_synthesizer=AngleSynthesizerAgent(day_key=_local_day_key(settings)),
        publisher=TopicWorkspacePublisher(settings.obsidian_root),
        snapshot_store=repo,
    )

    last_seen = repo.read_run_state("last_seen_attention_v2_ids")
    report = orchestrator.run(day_key=_local_day_key(settings), last_seen=last_seen)
    if report.next_seen_state:
        repo.mark_batch_run("last_seen_attention_v2_ids", report.next_seen_state)
    return report


def build_attention_client(settings):
    if not settings.attentionvc_api_key:
        return None
    return AttentionVCArticleClient(
        api_key=settings.attentionvc_api_key,
        base_url=settings.attentionvc_base_url,
    )


def build_crowd_context_service(settings, attention_client=None):
    client = attention_client or build_attention_client(settings)
    if client is None:
        return None

    summarizer = None
    if settings.writer_base_url and settings.writer_api_key and settings.writer_model:
        summarizer = LLMCrowdSummarizer(
            LLMWriterConfig(
                base_url=settings.writer_base_url,
                api_key=settings.writer_api_key,
                model=settings.writer_model,
                api_mode=settings.writer_api_mode,
                reasoning_effort=settings.writer_reasoning_effort,
                timeout_seconds=15.0,
            )
        )

    return CrowdContextService(
        client=client,
        reply_sample_limit=settings.attentionvc_reply_sample_limit,
        top_signal_count=settings.attentionvc_top_signal_count,
        summarizer=summarizer,
    )


def _local_day_key(settings) -> str:
    return SystemClock().now().astimezone(ZoneInfo(settings.timezone)).date().isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
