from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import tomllib


DEFAULT_LIST_ID = "2037242527036956865"
DEFAULT_RESEARCH_LOGIN = "Trieu"
DEFAULT_OBSIDIAN_VAULT = Path.home() / "Documents/Obsidian Vault"
DEFAULT_OBSIDIAN_ROOT_NAME = "推特运营Agent"
DEFAULT_TIMEZONE = "Asia/Shanghai"
DEFAULT_DAILY_CANDIDATE_BUDGET = 20
DEFAULT_BATCH_MODE = "manual_or_cron"
DEFAULT_CONFIG_RELATIVE_PATH = Path("config/settings.toml")
ENV_PREFIX = "TWITTER_OPS_AGENT_"


@dataclass(slots=True)
class AppSettings:
    list_id: str
    opencli_profile_name: str
    obsidian_vault: Path
    obsidian_root: Path
    timezone: str
    daily_candidate_budget: int
    batch_mode: str
    high_signal_source_handles: tuple[str, ...]
    twscrape_db: Path
    twscrape_expected_login: str
    x_fetcher_script: Path
    x_fetcher_browser: str
    sqlite_db: Path
    writer_base_url: str
    writer_api_key: str
    writer_model: str
    writer_api_mode: str
    writer_reasoning_effort: str
    attentionvc_api_key: str
    attentionvc_base_url: str
    attentionvc_categories: tuple[str, ...]
    attentionvc_window: str
    attentionvc_limit_per_category: int
    attentionvc_use_rising: bool
    attentionvc_rising_hours: int
    attentionvc_search_queries: tuple[str, ...]
    attentionvc_search_limit_per_query: int
    attentionvc_source_mode: str
    attentionvc_seed_min_views: int
    attentionvc_seed_min_likes: int
    attentionvc_seed_min_replies: int
    attentionvc_article_min_views: int
    attentionvc_article_min_likes: int
    attentionvc_article_min_replies: int
    attentionvc_tweet_min_views: int
    attentionvc_tweet_min_likes: int
    attentionvc_tweet_min_replies: int
    attentionvc_reply_sample_limit: int
    attentionvc_top_signal_count: int
    attentionvc_signal_min_views: int
    attentionvc_signal_min_likes: int
    attentionvc_signal_min_replies: int


def load_settings(config_path: Path | None = None, env: Mapping[str, str] | None = None) -> AppSettings:
    project_root = _project_root()

    values: dict[str, Any] = {
        "list_id": DEFAULT_LIST_ID,
        "opencli_profile_name": DEFAULT_RESEARCH_LOGIN,
        "obsidian_vault": DEFAULT_OBSIDIAN_VAULT,
        "obsidian_root": DEFAULT_OBSIDIAN_VAULT / DEFAULT_OBSIDIAN_ROOT_NAME,
        "timezone": DEFAULT_TIMEZONE,
        "daily_candidate_budget": 5,
        "batch_mode": DEFAULT_BATCH_MODE,
        "high_signal_source_handles": (),
        "twscrape_db": project_root / "data/twscrape/accounts.db",
        "twscrape_expected_login": DEFAULT_RESEARCH_LOGIN,
        "x_fetcher_script": project_root / "scripts/x-tweet-fetcher.py",
        "x_fetcher_browser": "camofox",
        "sqlite_db": project_root / "data/twitter_ops_agent.sqlite3",
        "writer_base_url": "",
        "writer_api_key": "",
        "writer_model": "",
        "writer_api_mode": "responses",
        "writer_reasoning_effort": "",
        "attentionvc_api_key": "",
        "attentionvc_base_url": "https://api.attentionvc.ai",
        "attentionvc_categories": ("ai", "crypto"),
        "attentionvc_window": "7d",
        "attentionvc_limit_per_category": 5,
        "attentionvc_use_rising": True,
        "attentionvc_rising_hours": 24,
        "attentionvc_search_queries": ("anthropic", "openai", "solana"),
        "attentionvc_search_limit_per_query": 3,
        "attentionvc_source_mode": "articles_only",
        "attentionvc_seed_min_views": 1000,
        "attentionvc_seed_min_likes": 20,
        "attentionvc_seed_min_replies": 5,
        "attentionvc_article_min_views": 2000,
        "attentionvc_article_min_likes": 20,
        "attentionvc_article_min_replies": 5,
        "attentionvc_tweet_min_views": 500,
        "attentionvc_tweet_min_likes": 10,
        "attentionvc_tweet_min_replies": 3,
        "attentionvc_reply_sample_limit": 100,
        "attentionvc_top_signal_count": 10,
        "attentionvc_signal_min_views": 100,
        "attentionvc_signal_min_likes": 1,
        "attentionvc_signal_min_replies": 1,
    }

    if config_path is not None:
        values.update(_load_config_file(config_path, project_root))

    values.update(_load_env_overrides(env or {}, project_root))

    obsidian_vault = _coerce_path(values["obsidian_vault"], project_root)
    obsidian_root = _coerce_path(
        values.get("obsidian_root", obsidian_vault / DEFAULT_OBSIDIAN_ROOT_NAME),
        project_root,
    )

    return AppSettings(
        list_id=str(values["list_id"]),
        opencli_profile_name=str(values["opencli_profile_name"]),
        obsidian_vault=obsidian_vault,
        obsidian_root=obsidian_root,
        timezone=str(values["timezone"]),
        daily_candidate_budget=int(values["daily_candidate_budget"]),
        batch_mode=str(values["batch_mode"]),
        high_signal_source_handles=tuple(str(item) for item in values["high_signal_source_handles"]),
        twscrape_db=_coerce_path(values["twscrape_db"], project_root),
        twscrape_expected_login=str(values["twscrape_expected_login"]),
        x_fetcher_script=_coerce_path(values["x_fetcher_script"], project_root),
        x_fetcher_browser=str(values["x_fetcher_browser"]),
        sqlite_db=_coerce_path(values["sqlite_db"], project_root),
        writer_base_url=str(values["writer_base_url"]),
        writer_api_key=str(values["writer_api_key"]),
        writer_model=str(values["writer_model"]),
        writer_api_mode=str(values["writer_api_mode"]),
        writer_reasoning_effort=str(values["writer_reasoning_effort"]),
        attentionvc_api_key=str(values["attentionvc_api_key"]),
        attentionvc_base_url=str(values["attentionvc_base_url"]),
        attentionvc_categories=tuple(str(item) for item in values["attentionvc_categories"]),
        attentionvc_window=str(values["attentionvc_window"]),
        attentionvc_limit_per_category=int(values["attentionvc_limit_per_category"]),
        attentionvc_use_rising=bool(values["attentionvc_use_rising"]),
        attentionvc_rising_hours=int(values["attentionvc_rising_hours"]),
        attentionvc_search_queries=tuple(str(item) for item in values["attentionvc_search_queries"]),
        attentionvc_search_limit_per_query=int(values["attentionvc_search_limit_per_query"]),
        attentionvc_source_mode=str(values["attentionvc_source_mode"]),
        attentionvc_seed_min_views=int(values["attentionvc_seed_min_views"]),
        attentionvc_seed_min_likes=int(values["attentionvc_seed_min_likes"]),
        attentionvc_seed_min_replies=int(values["attentionvc_seed_min_replies"]),
        attentionvc_article_min_views=int(values["attentionvc_article_min_views"]),
        attentionvc_article_min_likes=int(values["attentionvc_article_min_likes"]),
        attentionvc_article_min_replies=int(values["attentionvc_article_min_replies"]),
        attentionvc_tweet_min_views=int(values["attentionvc_tweet_min_views"]),
        attentionvc_tweet_min_likes=int(values["attentionvc_tweet_min_likes"]),
        attentionvc_tweet_min_replies=int(values["attentionvc_tweet_min_replies"]),
        attentionvc_reply_sample_limit=int(values["attentionvc_reply_sample_limit"]),
        attentionvc_top_signal_count=int(values["attentionvc_top_signal_count"]),
        attentionvc_signal_min_views=int(values["attentionvc_signal_min_views"]),
        attentionvc_signal_min_likes=int(values["attentionvc_signal_min_likes"]),
        attentionvc_signal_min_replies=int(values["attentionvc_signal_min_replies"]),
    )


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_config_path(project_root: Path | None = None) -> Path:
    root = project_root or _project_root()
    return root / DEFAULT_CONFIG_RELATIVE_PATH


def resolve_config_path(config_path: Path | None = None) -> Path | None:
    if config_path is not None:
        return config_path

    candidate = default_config_path()
    if candidate.exists():
        return candidate
    return None


def _load_config_file(config_path: Path, base_dir: Path) -> dict[str, Any]:
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    return _normalize_values(raw, base_dir)


def _load_env_overrides(env: Mapping[str, str], base_dir: Path) -> dict[str, Any]:
    overrides: dict[str, Any] = {}

    for field_name in AppSettings.__dataclass_fields__:
        env_name = f"{ENV_PREFIX}{field_name.upper()}"
        if env_name not in env:
            continue

        value = env[env_name]
        if field_name == "daily_candidate_budget":
            overrides[field_name] = int(value)
        elif field_name in {"high_signal_source_handles", "attentionvc_categories", "attentionvc_search_queries"}:
            overrides[field_name] = _coerce_str_tuple(value)
        elif field_name in {
            "attentionvc_limit_per_category",
            "attentionvc_rising_hours",
            "attentionvc_search_limit_per_query",
            "attentionvc_seed_min_views",
            "attentionvc_seed_min_likes",
            "attentionvc_seed_min_replies",
            "attentionvc_article_min_views",
            "attentionvc_article_min_likes",
            "attentionvc_article_min_replies",
            "attentionvc_tweet_min_views",
            "attentionvc_tweet_min_likes",
            "attentionvc_tweet_min_replies",
            "attentionvc_reply_sample_limit",
            "attentionvc_top_signal_count",
            "attentionvc_signal_min_views",
            "attentionvc_signal_min_likes",
            "attentionvc_signal_min_replies",
        }:
            overrides[field_name] = int(value)
        elif field_name == "attentionvc_use_rising":
            overrides[field_name] = _coerce_bool(value)
        elif field_name in {"obsidian_vault", "obsidian_root", "twscrape_db", "x_fetcher_script", "sqlite_db"}:
            overrides[field_name] = _coerce_path(value, base_dir)
        else:
            overrides[field_name] = value

    return overrides


def _normalize_values(raw: Mapping[str, Any], base_dir: Path) -> dict[str, Any]:
    normalized: dict[str, Any] = {}

    for key, value in raw.items():
        if key in {"obsidian_vault", "obsidian_root", "twscrape_db", "x_fetcher_script", "sqlite_db"}:
            normalized[key] = _coerce_path(value, base_dir)
        elif key in {"high_signal_source_handles", "attentionvc_categories", "attentionvc_search_queries"}:
            normalized[key] = _coerce_str_tuple(value)
        else:
            normalized[key] = value

    return normalized


def _coerce_path(value: Any, base_dir: Path) -> Path:
    path = value if isinstance(value, Path) else Path(str(value))
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def _coerce_str_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(item.strip() for item in value.split(",") if item.strip())
    return tuple(str(item) for item in value)


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "yes", "on"}
