from pathlib import Path

from twitter_ops_agent.cli import build_parser, build_v2_runtime, build_xhunt_scout
from twitter_ops_agent.config import load_settings


def test_cli_parser_accepts_run_v2():
    parser = build_parser()
    args = parser.parse_args(["run-v2"])
    assert args.command == "run-v2"


def test_build_v2_runtime_falls_back_to_xhunt_and_twscrape_when_attentionvc_is_missing(monkeypatch, tmp_path: Path):
    settings = load_settings(config_path=None, env={})
    repo = object()

    monkeypatch.setattr("twitter_ops_agent.cli.build_attention_client", lambda settings: None)
    monkeypatch.setattr("twitter_ops_agent.cli.build_xhunt_scout", lambda settings: "xhunt-scout")
    monkeypatch.setattr("twitter_ops_agent.cli.build_twscrape_crowd_client", lambda settings: "twscrape-client")
    monkeypatch.setattr("twitter_ops_agent.cli.EventService", lambda repo: "events")

    class StubHydration:
        def __init__(self, repo, events, source_fetcher=None):
            self.repo = repo
            self.events = events
            self.source_fetcher = source_fetcher

    monkeypatch.setattr("twitter_ops_agent.cli.HydrationAgent", StubHydration)

    runtime = build_v2_runtime(settings, repo)

    assert runtime["source_name"] == "xhunt+twscrape"
    assert runtime["state_key"] == "last_seen_xhunt_v2_ids"
    assert runtime["scout"] == "xhunt-scout"
    assert runtime["crowd_client"] == "twscrape-client"
    assert runtime["hydration"].source_fetcher == "twscrape-client"


def test_build_v2_runtime_prefers_browser_session_over_twscrape(monkeypatch):
    settings = load_settings(
        config_path=None,
        env={
            "TWITTER_OPS_AGENT_X_SESSION_COOKIE_HEADER": "auth_token=demo; ct0=demo",
            "TWITTER_OPS_AGENT_X_SESSION_X_CLIENT_TRANSACTION_ID": "browser123",
        },
    )
    repo = object()

    monkeypatch.setattr("twitter_ops_agent.cli.build_attention_client", lambda settings: None)
    monkeypatch.setattr("twitter_ops_agent.cli.build_xhunt_scout", lambda settings: "xhunt-scout")
    monkeypatch.setattr("twitter_ops_agent.cli.build_browser_x_session_client", lambda settings: "browser-client")
    monkeypatch.setattr("twitter_ops_agent.cli.build_twscrape_crowd_client", lambda settings: "twscrape-client")
    monkeypatch.setattr("twitter_ops_agent.cli.EventService", lambda repo: "events")

    class StubHydration:
        def __init__(self, repo, events, source_fetcher=None):
            self.source_fetcher = source_fetcher

    monkeypatch.setattr("twitter_ops_agent.cli.HydrationAgent", StubHydration)

    runtime = build_v2_runtime(settings, repo)

    assert runtime["source_name"] == "xhunt+browser-session"
    assert runtime["crowd_client"] == "browser-client"
    assert runtime["hydration"].source_fetcher == "browser-client"


def test_build_xhunt_scout_uses_dual_group_defaults():
    settings = load_settings(config_path=None, env={})

    scout = build_xhunt_scout(settings)

    assert scout.groups == ("cn", "global")
    assert scout.hours == 24
    assert scout.limit == 15
