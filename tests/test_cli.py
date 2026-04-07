from pathlib import Path

from twitter_ops_agent.cli import build_cross_signal_runtime, build_parser, build_v2_runtime, build_xhunt_scout, main
from twitter_ops_agent.config import load_settings


def test_cli_parser_accepts_run_v2():
    parser = build_parser()
    args = parser.parse_args(["run-v2"])
    assert args.command == "run-v2"


def test_cli_parser_accepts_cross_signal():
    parser = build_parser()
    args = parser.parse_args(["cross-signal"])
    assert args.command == "cross-signal"


def test_cli_parser_accepts_cross_signal_save_to(tmp_path: Path):
    parser = build_parser()
    out_path = tmp_path / "latest.json"
    args = parser.parse_args(["cross-signal", "--save-to", str(out_path), "--review-all"])

    assert args.command == "cross-signal"
    assert args.save_to == out_path
    assert args.review_all is True


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


def test_build_cross_signal_runtime_uses_cross_signal_thresholds(monkeypatch):
    settings = load_settings(
        config_path=None,
        env={
            "TWITTER_OPS_AGENT_CROSS_SIGNAL_MIN_POSTS": "4",
            "TWITTER_OPS_AGENT_CROSS_SIGNAL_MIN_ACCOUNTS": "3",
            "TWITTER_OPS_AGENT_CROSS_SIGNAL_SEARCH_LIMIT": "25",
            "TWITTER_OPS_AGENT_CROSS_SIGNAL_CANDIDATE_LIMIT": "2",
        },
    )
    sentinel_scout = object()
    sentinel_client = object()

    monkeypatch.setattr(
        "twitter_ops_agent.cli.PolymarketSignalScout",
        lambda candidate_limit=0, filter_candidates=False: {
            "scout": sentinel_scout,
            "candidate_limit": candidate_limit,
            "filter_candidates": filter_candidates,
        },
    )
    monkeypatch.setattr("twitter_ops_agent.cli.TwscrapeCrowdClient.from_db", lambda *args, **kwargs: sentinel_client)
    runtime = build_cross_signal_runtime(settings)

    assert runtime["scout"]["scout"] is sentinel_scout
    assert runtime["scout"]["candidate_limit"] == 2
    assert runtime["scout"]["filter_candidates"] is False
    assert runtime["gate"].client is sentinel_client
    assert runtime["gate"].min_posts == 4
    assert runtime["gate"].min_accounts == 3
    assert runtime["gate"].search_limit == 25


def test_build_cross_signal_runtime_prefers_grok_when_xai_config_present(monkeypatch):
    settings = load_settings(
        config_path=None,
        env={
            "TWITTER_OPS_AGENT_CROSS_SIGNAL_XAI_API_KEY": "secret",
        },
    )
    sentinel_scout = object()
    sentinel_gate = object()

    monkeypatch.setattr(
        "twitter_ops_agent.cli.PolymarketSignalScout",
        lambda candidate_limit=0, filter_candidates=False: {
            "scout": sentinel_scout,
            "candidate_limit": candidate_limit,
            "filter_candidates": filter_candidates,
        },
    )
    monkeypatch.setattr("twitter_ops_agent.cli.build_grok_cross_signal_gate", lambda settings: sentinel_gate)

    runtime = build_cross_signal_runtime(settings)

    assert runtime["scout"]["scout"] is sentinel_scout
    assert runtime["scout"]["candidate_limit"] == 0
    assert runtime["scout"]["filter_candidates"] is False
    assert runtime["gate"] is sentinel_gate


def test_main_cross_signal_prints_new_candidate_count(monkeypatch, capsys):
    monkeypatch.setattr("twitter_ops_agent.cli.resolve_config_path", lambda config: None)
    monkeypatch.setattr("twitter_ops_agent.cli.load_settings", lambda config_path, env: object())

    class StubReport:
        candidate_count = 5
        new_candidate_count = 2
        passed_count = 1
        topics = ()
        candidates = ()
        new_candidates = ()
        reviewed_candidates = ()

    class StubOrchestrator:
        def run(self, review_all=False):
            return StubReport()

    monkeypatch.setattr("twitter_ops_agent.cli.build_cross_signal_orchestrator", lambda settings: StubOrchestrator())

    exit_code = main(["cross-signal"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert '"new_candidate_count": 2' in output


def test_main_cross_signal_prints_json_report(monkeypatch, capsys):
    monkeypatch.setattr("twitter_ops_agent.cli.resolve_config_path", lambda config: None)
    monkeypatch.setattr("twitter_ops_agent.cli.load_settings", lambda config_path, env: object())

    class StubReport:
        candidate_count = 2
        new_candidate_count = 1
        passed_count = 1
        topics = ()
        candidates = ()
        new_candidates = ()
        reviewed_candidates = ()

    class StubOrchestrator:
        def run(self, review_all=False):
            return StubReport()

    monkeypatch.setattr("twitter_ops_agent.cli.build_cross_signal_orchestrator", lambda settings: StubOrchestrator())

    exit_code = main(["cross-signal"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert '"candidate_count": 2' in output
    assert '"passed_count": 1' in output


def test_main_cross_signal_can_save_json_report(monkeypatch, capsys, tmp_path: Path):
    monkeypatch.setattr("twitter_ops_agent.cli.resolve_config_path", lambda config: None)
    monkeypatch.setattr("twitter_ops_agent.cli.load_settings", lambda config_path, env: object())

    class StubReport:
        candidate_count = 1
        new_candidate_count = 1
        passed_count = 1
        topics = ()
        candidates = ()
        new_candidates = ()
        reviewed_candidates = ()

    class StubOrchestrator:
        def run(self, review_all=False):
            return StubReport()

    monkeypatch.setattr("twitter_ops_agent.cli.build_cross_signal_orchestrator", lambda settings: StubOrchestrator())
    out_path = tmp_path / "latest.json"

    exit_code = main(["cross-signal", "--save-to", str(out_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert out_path.exists()
    assert '"candidate_count": 1' in output
    assert '"passed_count": 1' in out_path.read_text(encoding="utf-8")
