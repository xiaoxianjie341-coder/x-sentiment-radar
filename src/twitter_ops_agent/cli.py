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
from twitter_ops_agent.discovery.polymarket import PolymarketSignalScout
from twitter_ops_agent.discovery.xhunt import XHuntScoutAgent, XHuntTrendClient
from twitter_ops_agent.doctor import run_doctor
from twitter_ops_agent.domain.models import CrossSignalAlert, CrossSignalPost
from twitter_ops_agent.events.linker import EventService
from twitter_ops_agent.research.browser_x_client import BrowserXSessionCrowdClient
from twitter_ops_agent.research.crowd_context import CrowdContextService, LLMCrowdSummarizer
from twitter_ops_agent.research.twscrape_client import TwscrapeCrowdClient
from twitter_ops_agent.storage.repository import SqliteRepository
from twitter_ops_agent.v2.agents.cross_signal_gate import CrossSignalGate
from twitter_ops_agent.v2.agents.grok_cross_signal_gate import GrokCrossSignalGate, XaiSearchConfig
from twitter_ops_agent.v2.agents.angle_synthesizer import AngleSynthesizerAgent
from twitter_ops_agent.v2.agents.crowd_sense import CrowdSenseAgent
from twitter_ops_agent.v2.agents.hydration_agent import HydrationAgent
from twitter_ops_agent.v2.agents.priority_gate import PriorityGateAgent
from twitter_ops_agent.v2.agents.topic_scout import TopicScoutAgent
from twitter_ops_agent.v2.cross_signal import CrossSignalOrchestrator
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
    cross_signal_parser = subcommands.add_parser("cross-signal", help="Run the Polymarket + X cross-signal monitor.")
    cross_signal_parser.add_argument("--save-to", type=Path, default=None, help="Optional path to save the JSON report.")
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

    if args.command == "cross-signal":
        try:
            report = build_cross_signal_orchestrator(settings).run()
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
            return 1
        payload = json.dumps(
            {
                "candidate_count": report.candidate_count,
                "passed_count": report.passed_count,
                "topics": [_serialize_cross_signal_alert(item) for item in report.topics],
            },
            ensure_ascii=False,
            indent=2,
        )
        print(payload)
        if args.save_to is not None:
            args.save_to.parent.mkdir(parents=True, exist_ok=True)
            args.save_to.write_text(payload + "\n", encoding="utf-8")
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2


class SystemClock:
    def now(self):
        import datetime as _datetime

        return _datetime.datetime.now(_datetime.timezone.utc)


def run_v2(settings):
    repo = SqliteRepository(settings.sqlite_db)
    runtime = build_v2_runtime(settings, repo)
    orchestrator = V2Orchestrator(
        scout=runtime["scout"],
        hydration=runtime["hydration"],
        priority_gate=PriorityGateAgent(daily_budget=settings.daily_candidate_budget),
        crowd_sense=CrowdSenseAgent(
            crowd_context=build_crowd_context_service(settings, client=runtime["crowd_client"]),
            signal_min_views=settings.attentionvc_signal_min_views,
            signal_min_likes=settings.attentionvc_signal_min_likes,
            signal_min_replies=settings.attentionvc_signal_min_replies,
        ),
        angle_synthesizer=AngleSynthesizerAgent(day_key=_local_day_key(settings)),
        publisher=TopicWorkspacePublisher(settings.obsidian_root),
        snapshot_store=repo,
    )

    last_seen = repo.read_run_state(runtime["state_key"])
    report = orchestrator.run(day_key=_local_day_key(settings), last_seen=last_seen)
    if report.next_seen_state:
        repo.mark_batch_run(runtime["state_key"], report.next_seen_state)
    return report


def build_v2_runtime(settings, repo):
    attention_client = build_attention_client(settings)
    if attention_client is not None:
        return {
            "source_name": "attentionvc",
            "state_key": "last_seen_attention_v2_ids",
            "scout": TopicScoutAgent(
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
            "hydration": HydrationAgent(repo=repo, events=EventService(repo)),
            "crowd_client": attention_client,
        }

    browser_client = build_browser_x_session_client(settings)
    if browser_client is not None:
        return {
            "source_name": "xhunt+browser-session",
            "state_key": "last_seen_xhunt_v2_ids",
            "scout": build_xhunt_scout(settings),
            "hydration": HydrationAgent(repo=repo, events=EventService(repo), source_fetcher=browser_client),
            "crowd_client": browser_client,
        }

    crowd_client = build_twscrape_crowd_client(settings)
    if crowd_client is None:
        raise RuntimeError("run-v2 requires AttentionVC, a browser-backed X session, or a working twscrape install.")
    return {
        "source_name": "xhunt+twscrape",
        "state_key": "last_seen_xhunt_v2_ids",
        "scout": build_xhunt_scout(settings),
        "hydration": HydrationAgent(repo=repo, events=EventService(repo), source_fetcher=crowd_client),
        "crowd_client": crowd_client,
    }


def build_attention_client(settings):
    if not settings.attentionvc_api_key:
        return None
    return AttentionVCArticleClient(
        api_key=settings.attentionvc_api_key,
        base_url=settings.attentionvc_base_url,
    )


def build_crowd_context_service(settings, client=None):
    client = client or build_attention_client(settings)
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


def build_xhunt_client(settings):
    return XHuntTrendClient(base_url=settings.xhunt_base_url)


def build_xhunt_scout(settings):
    return XHuntScoutAgent(
        client=build_xhunt_client(settings),
        groups=settings.xhunt_groups,
        hours=settings.xhunt_hours,
        limit=settings.xhunt_limit,
        min_views=settings.xhunt_min_views,
        min_likes=settings.xhunt_min_likes,
    )


def build_twscrape_crowd_client(settings):
    return TwscrapeCrowdClient.from_db(
        settings.twscrape_db,
        search_enabled=settings.twscrape_search_enabled,
        x_client_transaction_id=settings.twscrape_x_client_transaction_id,
    )


def build_browser_x_session_client(settings):
    if not settings.x_session_cookie_header or not settings.x_session_x_client_transaction_id:
        return None
    return BrowserXSessionCrowdClient(
        cookie_header=settings.x_session_cookie_header,
        x_client_transaction_id=settings.x_session_x_client_transaction_id,
        user_agent=settings.x_session_user_agent,
    )


def build_cross_signal_runtime(settings):
    scout = PolymarketSignalScout(
        candidate_limit=settings.cross_signal_candidate_limit,
        filter_candidates=settings.cross_signal_filter_candidates,
    )
    if settings.cross_signal_xai_api_key and settings.cross_signal_xai_model:
        return {
            "scout": scout,
            "gate": build_grok_cross_signal_gate(settings),
        }
    return {
        "scout": scout,
        "gate": CrossSignalGate(
            client=TwscrapeCrowdClient.from_db(
                settings.twscrape_db,
                search_enabled=True,
                x_client_transaction_id=settings.twscrape_x_client_transaction_id,
            ),
            min_posts=settings.cross_signal_min_posts,
            min_accounts=settings.cross_signal_min_accounts,
            search_limit=settings.cross_signal_search_limit,
            top_post_limit=settings.cross_signal_top_post_limit,
        ),
    }


def build_cross_signal_orchestrator(settings):
    runtime = build_cross_signal_runtime(settings)
    return CrossSignalOrchestrator(
        scout=runtime["scout"],
        gate=runtime["gate"],
    )


def build_grok_cross_signal_gate(settings):
    return GrokCrossSignalGate(
        config=XaiSearchConfig(
            api_key=settings.cross_signal_xai_api_key,
            base_url=settings.cross_signal_xai_base_url,
            model=settings.cross_signal_xai_model,
            reasoning_effort=settings.cross_signal_xai_reasoning_effort,
        )
    )


def _serialize_cross_signal_alert(alert: CrossSignalAlert) -> dict[str, object]:
    return {
        "topic": alert.topic,
        "market_title": alert.market_title,
        "market_url": alert.market_url,
        "source_label": alert.source_label,
        "queries": list(alert.queries),
        "angle_summary": alert.angle_summary,
        "distinct_post_count": alert.distinct_post_count,
        "distinct_account_count": alert.distinct_account_count,
        "verification_passed": alert.verification_passed,
        "top_posts": [_serialize_cross_signal_post(post) for post in alert.top_posts],
    }


def _serialize_cross_signal_post(post: CrossSignalPost) -> dict[str, object]:
    return {
        "tweet_id": post.tweet_id,
        "author_handle": post.author_handle,
        "text": post.text,
        "url": post.url,
        "likes": post.likes,
        "retweets": post.retweets,
        "replies": post.replies,
        "quotes": post.quotes,
        "views": post.views,
        "spread_score": post.spread_score,
    }


def _local_day_key(settings) -> str:
    return SystemClock().now().astimezone(ZoneInfo(settings.timezone)).date().isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
