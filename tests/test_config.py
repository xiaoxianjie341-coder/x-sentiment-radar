from pathlib import Path

from twitter_ops_agent.config import load_settings


def test_load_settings_defaults_obsidian_contract():
    settings = load_settings(config_path=None, env={})

    assert settings.list_id == "2037242527036956865"
    assert settings.opencli_profile_name == "Trieu"
    assert settings.obsidian_vault == Path.home() / "Documents/Obsidian Vault"
    assert settings.obsidian_root.name == "推特运营Agent"
    assert settings.timezone == "Asia/Shanghai"
    assert settings.daily_candidate_budget == 5
    assert settings.batch_mode == "manual_or_cron"
    assert settings.writer_base_url == ""
    assert settings.writer_api_key == ""
    assert settings.writer_model == ""
    assert settings.writer_api_mode == "responses"
    assert settings.attentionvc_api_key == ""
    assert settings.attentionvc_categories == ("ai", "crypto")
    assert settings.attentionvc_use_rising is True
    assert settings.attentionvc_search_queries == ("anthropic", "openai", "solana")
    assert settings.attentionvc_top_signal_count == 5
    assert settings.attentionvc_source_mode == "mixed"
    assert settings.attentionvc_seed_min_views == 1000
    assert settings.attentionvc_article_min_views == 3000
    assert settings.attentionvc_tweet_min_views == 500


def test_load_settings_example_config_resolves_repo_relative_paths():
    repo_root = Path(__file__).resolve().parents[1]

    settings = load_settings(
        config_path=repo_root / "config/settings.example.toml",
        env={},
    )

    assert settings.twscrape_db == repo_root / "data/twscrape/accounts.db"
    assert settings.x_fetcher_script == repo_root / "scripts/x-tweet-fetcher.py"
    assert settings.sqlite_db == repo_root / "data/twitter_ops_agent.sqlite3"


def test_load_settings_supports_writer_env_overrides():
    settings = load_settings(
        config_path=None,
        env={
            "TWITTER_OPS_AGENT_WRITER_BASE_URL": "https://example.com/v1",
            "TWITTER_OPS_AGENT_WRITER_API_KEY": "secret-key",
            "TWITTER_OPS_AGENT_WRITER_MODEL": "gpt-5",
            "TWITTER_OPS_AGENT_WRITER_API_MODE": "chat_completions",
            "TWITTER_OPS_AGENT_WRITER_REASONING_EFFORT": "high",
        },
    )

    assert settings.writer_base_url == "https://example.com/v1"
    assert settings.writer_api_key == "secret-key"
    assert settings.writer_model == "gpt-5"
    assert settings.writer_api_mode == "chat_completions"
    assert settings.writer_reasoning_effort == "high"


def test_load_settings_supports_attentionvc_env_overrides():
    settings = load_settings(
        config_path=None,
        env={
            "TWITTER_OPS_AGENT_ATTENTIONVC_API_KEY": "avc_test_key",
            "TWITTER_OPS_AGENT_ATTENTIONVC_CATEGORIES": "ai,crypto",
            "TWITTER_OPS_AGENT_ATTENTIONVC_WINDOW": "14d",
            "TWITTER_OPS_AGENT_ATTENTIONVC_LIMIT_PER_CATEGORY": "8",
            "TWITTER_OPS_AGENT_ATTENTIONVC_USE_RISING": "true",
            "TWITTER_OPS_AGENT_ATTENTIONVC_RISING_HOURS": "48",
            "TWITTER_OPS_AGENT_ATTENTIONVC_SEARCH_QUERIES": "anthropic,solana",
            "TWITTER_OPS_AGENT_ATTENTIONVC_SEARCH_LIMIT_PER_QUERY": "6",
            "TWITTER_OPS_AGENT_ATTENTIONVC_SOURCE_MODE": "tweets_only",
            "TWITTER_OPS_AGENT_ATTENTIONVC_SEED_MIN_VIEWS": "2000",
            "TWITTER_OPS_AGENT_ATTENTIONVC_SEED_MIN_LIKES": "30",
            "TWITTER_OPS_AGENT_ATTENTIONVC_SEED_MIN_REPLIES": "6",
            "TWITTER_OPS_AGENT_ATTENTIONVC_ARTICLE_MIN_VIEWS": "5000",
            "TWITTER_OPS_AGENT_ATTENTIONVC_ARTICLE_MIN_LIKES": "50",
            "TWITTER_OPS_AGENT_ATTENTIONVC_ARTICLE_MIN_REPLIES": "20",
            "TWITTER_OPS_AGENT_ATTENTIONVC_TWEET_MIN_VIEWS": "800",
            "TWITTER_OPS_AGENT_ATTENTIONVC_TWEET_MIN_LIKES": "12",
            "TWITTER_OPS_AGENT_ATTENTIONVC_TWEET_MIN_REPLIES": "4",
            "TWITTER_OPS_AGENT_ATTENTIONVC_REPLY_SAMPLE_LIMIT": "15",
            "TWITTER_OPS_AGENT_ATTENTIONVC_TOP_SIGNAL_COUNT": "4",
            "TWITTER_OPS_AGENT_ATTENTIONVC_SIGNAL_MIN_VIEWS": "80",
            "TWITTER_OPS_AGENT_ATTENTIONVC_SIGNAL_MIN_LIKES": "2",
            "TWITTER_OPS_AGENT_ATTENTIONVC_SIGNAL_MIN_REPLIES": "2",
        },
    )

    assert settings.attentionvc_api_key == "avc_test_key"
    assert settings.attentionvc_categories == ("ai", "crypto")
    assert settings.attentionvc_window == "14d"
    assert settings.attentionvc_limit_per_category == 8
    assert settings.attentionvc_use_rising is True
    assert settings.attentionvc_rising_hours == 48
    assert settings.attentionvc_search_queries == ("anthropic", "solana")
    assert settings.attentionvc_search_limit_per_query == 6
    assert settings.attentionvc_source_mode == "tweets_only"
    assert settings.attentionvc_seed_min_views == 2000
    assert settings.attentionvc_seed_min_likes == 30
    assert settings.attentionvc_seed_min_replies == 6
    assert settings.attentionvc_article_min_views == 5000
    assert settings.attentionvc_article_min_likes == 50
    assert settings.attentionvc_article_min_replies == 20
    assert settings.attentionvc_tweet_min_views == 800
    assert settings.attentionvc_tweet_min_likes == 12
    assert settings.attentionvc_tweet_min_replies == 4
    assert settings.attentionvc_reply_sample_limit == 15
    assert settings.attentionvc_top_signal_count == 4
    assert settings.attentionvc_signal_min_views == 80
    assert settings.attentionvc_signal_min_likes == 2
    assert settings.attentionvc_signal_min_replies == 2
