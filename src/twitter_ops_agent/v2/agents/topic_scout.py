from __future__ import annotations

import json
import re

from twitter_ops_agent.discovery.attentionvc import AttentionArticle, AttentionTweet, AttentionVCArticleClient
from twitter_ops_agent.filter.track import classify_track
from twitter_ops_agent.v2.contracts import ScoutRunResult, ScoutSeed


class TopicScoutAgent:
    def __init__(
        self,
        *,
        client: AttentionVCArticleClient,
        categories: tuple[str, ...] = ("ai", "crypto"),
        article_window: str = "7d",
        article_limit_per_category: int = 10,
        use_rising_articles: bool = False,
        rising_hours: int = 24,
        search_queries: tuple[str, ...] = (),
        topic_query_limit: int = 6,
        search_limit_per_query: int = 5,
        source_mode: str = "mixed",
        seed_min_views: int = 1000,
        seed_min_likes: int = 20,
        seed_min_replies: int = 5,
        article_min_views: int | None = None,
        article_min_likes: int | None = None,
        article_min_replies: int | None = None,
        tweet_min_views: int | None = None,
        tweet_min_likes: int | None = None,
        tweet_min_replies: int | None = None,
        state_size: int = 200,
    ) -> None:
        self.client = client
        self.categories = categories
        self.article_window = article_window
        self.article_limit_per_category = article_limit_per_category
        self.use_rising_articles = use_rising_articles
        self.rising_hours = rising_hours
        self.search_queries = search_queries
        self.topic_query_limit = topic_query_limit
        self.search_limit_per_query = search_limit_per_query
        self.source_mode = source_mode
        self.seed_min_views = seed_min_views
        self.seed_min_likes = seed_min_likes
        self.seed_min_replies = seed_min_replies
        self.article_min_views = article_min_views if article_min_views is not None else seed_min_views
        self.article_min_likes = article_min_likes if article_min_likes is not None else seed_min_likes
        self.article_min_replies = article_min_replies if article_min_replies is not None else seed_min_replies
        self.tweet_min_views = tweet_min_views if tweet_min_views is not None else seed_min_views
        self.tweet_min_likes = tweet_min_likes if tweet_min_likes is not None else seed_min_likes
        self.tweet_min_replies = tweet_min_replies if tweet_min_replies is not None else seed_min_replies
        self.state_size = state_size

    def fetch_since(self, last_seen: str | None) -> ScoutRunResult:
        previous_seen = _parse_seen_state(last_seen)
        seen_ids = set(previous_seen)
        seeds: list[ScoutSeed] = []
        article_seed_pool: list[ScoutSeed] = []
        if self.source_mode in {"mixed", "articles_only"}:
            for category in self.categories or (None,):
                if self.use_rising_articles:
                    for article in self.client.rising_articles(
                        category=category,
                        hours=self.rising_hours,
                        limit=self.article_limit_per_category,
                    ):
                        seed = _seed_from_article(article)
                        if _passes_seed_thresholds(seed, self):
                            article_seed_pool.append(seed)
                for article in self.client.list_articles(
                    category=category,
                    window=self.article_window,
                    limit=self.article_limit_per_category,
                ):
                    seed = _seed_from_article(article)
                    if _passes_seed_thresholds(seed, self):
                        article_seed_pool.append(seed)
        seeds.extend(article_seed_pool)
        if self.source_mode in {"mixed", "tweets_only"}:
            topic_queries = tuple(
                _dedupe_preserve_order(
                    [
                        *self.search_queries,
                        *_topic_queries_from_articles(article_seed_pool, limit=self.topic_query_limit),
                        *_topic_queries_from_platform(self.client, self.categories, self.article_window, limit=self.topic_query_limit),
                    ]
                )
            )
            for query in topic_queries:
                for tweet in self.client.search_tweets(query=query, limit=self.search_limit_per_query):
                    seed = _seed_from_tweet(tweet, query=query)
                    if _passes_seed_thresholds(seed, self):
                        seeds.append(seed)

        deduped = _dedupe_and_sort(seeds)
        fresh = [seed for seed in deduped if seed.tweet_id not in seen_ids]
        next_seen_state = json.dumps(_merge_seen_ids([seed.tweet_id for seed in deduped], previous_seen, self.state_size), ensure_ascii=False)
        return ScoutRunResult(seeds=fresh, next_seen_state=next_seen_state)

    def run(self) -> list[ScoutSeed]:
        return self.fetch_since(last_seen=None).seeds


def _seed_from_article(article: AttentionArticle) -> ScoutSeed:
    return ScoutSeed(
        seed_id=f"article:{article.tweet_id}",
        source_kind="article",
        query=article.category or "",
        tweet_id=article.tweet_id,
        url=article.url,
        text="\n\n".join(part for part in (article.title, article.preview_text) if part),
        title=article.title or article.preview_text or article.tweet_id,
        track=_map_article_track(article),
        author_handle=article.author_handle,
        views=article.views,
        replies=article.replies,
        likes=article.likes,
        velocity_hint=article.velocity_per_hour or 0.0,
    )


def _seed_from_tweet(tweet: AttentionTweet, *, query: str) -> ScoutSeed:
    track = classify_track(tweet.text, tweet.author_handle)
    title = " ".join(tweet.text.split())[:120] or tweet.tweet_id
    return ScoutSeed(
        seed_id=f"tweet:{tweet.tweet_id}",
        source_kind="tweet",
        query=query,
        tweet_id=tweet.tweet_id,
        url=tweet.url,
        text=tweet.text,
        title=title,
        track=track,
        author_handle=tweet.author_handle,
        views=tweet.views,
        replies=tweet.replies,
        likes=tweet.likes,
        velocity_hint=0.0,
    )


def _map_article_track(article: AttentionArticle) -> str | None:
    if article.category == "ai":
        return "AI"
    if article.category == "crypto":
        return "Crypto"
    return classify_track(f"{article.title}\n{article.preview_text}", article.author_handle)


def _topic_queries_from_articles(article_seeds: list[ScoutSeed], *, limit: int) -> list[str]:
    queries: list[str] = []
    for seed in article_seeds[:limit]:
        if seed.title:
            queries.append(_normalize_query(seed.title))
        if seed.query:
            queries.append(_normalize_query(seed.query))
    return [query for query in queries if query][:limit]


def _topic_queries_from_platform(client: AttentionVCArticleClient, categories: tuple[str, ...], window: str, *, limit: int) -> list[str]:
    queries: list[str] = []
    for topic in client.trending_topics(window=window):
        queries.append(_normalize_query(topic.name or topic.slug))
        if len(queries) >= limit:
            break
    for category in categories:
        insights = client.category_insights(category=category, window=window)
        for article in insights.get("topArticles", [])[:3]:
            queries.append(_normalize_query(str(article.get("title", ""))))
            queries.append(_normalize_query(str(article.get("author", ""))))
            if len(queries) >= limit * 2:
                break
        if len(queries) >= limit * 2:
            break
    return _dedupe_preserve_order([query for query in queries if query])[:limit]


def _normalize_query(value: str) -> str:
    compact = " ".join(value.split()).strip()
    compact = re.sub(r"[^\w\s\-一-龥]", " ", compact)
    compact = " ".join(compact.split())
    return compact[:80]


def _dedupe_and_sort(seeds: list[ScoutSeed]) -> list[ScoutSeed]:
    deduped: dict[str, ScoutSeed] = {}
    for seed in seeds:
        existing = deduped.get(seed.tweet_id)
        if existing is None or _seed_score(seed) > _seed_score(existing):
            deduped[seed.tweet_id] = seed
    return sorted(
        deduped.values(),
        key=lambda item: (
            -_seed_score(item),
            0 if item.source_kind == "tweet" else 1,
            item.tweet_id,
        ),
    )


def _seed_score(seed: ScoutSeed) -> float:
    return (
        seed.velocity_hint * 10
        + seed.replies * 8
        + seed.likes * 2
        + min(seed.views / 1000.0, 100.0)
    )


def _passes_seed_thresholds(seed: ScoutSeed, agent: TopicScoutAgent) -> bool:
    if seed.source_kind == "article":
        min_views = agent.article_min_views
        min_likes = agent.article_min_likes
        min_replies = agent.article_min_replies
    else:
        min_views = agent.tweet_min_views
        min_likes = agent.tweet_min_likes
        min_replies = agent.tweet_min_replies
    return (
        seed.views >= min_views
        and seed.likes >= min_likes
        and seed.replies >= min_replies
    )


def _parse_seen_state(last_seen: str | None) -> list[str]:
    if not last_seen:
        return []
    try:
        payload = json.loads(last_seen)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [str(item) for item in payload if str(item).strip()]


def _merge_seen_ids(current_ids: list[str], previous_seen: list[str], state_size: int) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for tweet_id in [*current_ids, *previous_seen]:
        if tweet_id in seen:
            continue
        seen.add(tweet_id)
        merged.append(tweet_id)
        if len(merged) >= state_size:
            break
    return merged


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = value.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(value.strip())
    return ordered
