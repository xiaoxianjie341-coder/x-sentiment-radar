from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
import json
import re
from typing import Any, Iterable, Mapping
from urllib import error, parse, request

from twitter_ops_agent.domain.models import Account, CaptureResult, Post, utc_now


@dataclass(slots=True)
class AttentionArticle:
    tweet_id: str
    title: str
    preview_text: str
    url: str
    published_at: datetime
    author_handle: str
    author_name: str
    author_followers: int
    author_is_blue_verified: bool
    views: int
    likes: int
    retweets: int
    replies: int
    quotes: int
    bookmarks: int
    category: str | None
    langs: tuple[str, ...]
    trending_topics: tuple[str, ...]
    velocity_per_hour: float | None = None


@dataclass(slots=True)
class AttentionTweet:
    tweet_id: str
    text: str
    url: str
    published_at: datetime
    author_handle: str
    author_name: str
    author_followers: int
    author_is_blue_verified: bool
    views: int
    likes: int
    retweets: int
    replies: int
    quotes: int
    bookmarks: int
    lang: str | None = None
    conversation_id: str | None = None


@dataclass(slots=True)
class AttentionBatch:
    captures: tuple[CaptureResult, ...]
    next_seen_state: str
    discovered_count: int


@dataclass(slots=True)
class AttentionTopic:
    slug: str
    name: str
    article_count: int
    total_views: int


class AttentionVCArticleClient:
    def __init__(self, api_key: str, *, base_url: str = "https://api.attentionvc.ai", timeout: float = 20.0) -> None:
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        if not self.api_key:
            raise ValueError("AttentionVC API key must not be empty.")

    def list_articles(
        self,
        *,
        category: str | None = None,
        window: str = "7d",
        limit: int = 20,
    ) -> list[AttentionArticle]:
        payload = self._get_json(
            "/v1/x/articles",
            {
                "category": category,
                "window": window,
                "limit": limit,
            },
        )
        return _parse_articles(payload.get("articles", ()))

    def rising_articles(
        self,
        *,
        category: str | None = None,
        hours: int = 24,
        limit: int = 20,
    ) -> list[AttentionArticle]:
        payload = self._get_json(
            "/v1/x/articles/rising",
            {
                "category": category,
                "hours": hours,
                "limit": limit,
            },
        )
        return _parse_articles(payload.get("articles", ()))

    def trending_topics(self, *, window: str = "7d") -> list[AttentionTopic]:
        payload = self._get_json("/v1/x/trending", {"window": window})
        return _parse_topics(payload.get("topics", ()))

    def category_insights(self, *, category: str, window: str = "7d") -> Mapping[str, Any]:
        return self._get_json(f"/v1/x/categories/{category}/insights", {"window": window})

    def search_tweets(self, *, query: str, limit: int = 20) -> list[AttentionTweet]:
        return self._paginate_tweets("/v1/x/search", limit=limit, query=query)

    def tweet_thread(self, *, tweet_id: str) -> list[AttentionTweet]:
        payload = self._get_json("/v1/x/tweet/thread", {"tweetId": tweet_id})
        return _parse_tweets(payload.get("tweets", ()))

    def tweet_replies(self, *, tweet_id: str, limit: int = 20) -> list[AttentionTweet]:
        tweets = self._paginate_tweets("/v1/x/tweet/replies", tweet_id=tweet_id, limit=limit)
        if tweets:
            return tweets[:limit]

        fallback = self._paginate_tweets("/v1/x/tweet/replies/v2", tweet_id=tweet_id, limit=limit)
        return fallback[:limit]

    def _get_json(self, path: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        query = parse.urlencode(
            [(key, value) for key, value in params.items() if value not in {None, ""}]
        )
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{query}"

        req = request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"AttentionVC request failed with HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"AttentionVC request failed: {exc.reason}") from exc

        if not payload.get("success", False):
            raise RuntimeError(f"AttentionVC request failed: {payload.get('error', 'unknown error')}")
        return payload.get("data", {})

    def _paginate_tweets(self, path: str, *, limit: int, tweet_id: str | None = None, query: str | None = None) -> list[AttentionTweet]:
        cursor: str | None = None
        collected: list[AttentionTweet] = []
        seen_ids: set[str] = set()
        while len(collected) < limit:
            params: dict[str, Any] = {}
            if tweet_id is not None:
                params["tweetId"] = tweet_id
            if query is not None:
                params["query"] = query
            if cursor:
                params["cursor"] = cursor
            payload = self._get_json(path, params)
            page = _parse_tweets(payload.get("tweets", ()))
            for tweet in page:
                if tweet.tweet_id in seen_ids:
                    continue
                seen_ids.add(tweet.tweet_id)
                collected.append(tweet)
                if len(collected) >= limit:
                    break
            if len(collected) >= limit:
                break
            if not payload.get("has_next_page"):
                break
            next_cursor = payload.get("next_cursor")
            if not next_cursor or next_cursor == cursor:
                break
            cursor = str(next_cursor)
        return collected


class AttentionVCDiscoveryService:
    def __init__(
        self,
        *,
        client: AttentionVCArticleClient,
        categories: tuple[str, ...] = ("ai", "crypto"),
        window: str = "7d",
        limit_per_category: int = 10,
        use_rising: bool = False,
        rising_hours: int = 24,
        search_queries: tuple[str, ...] = (),
        search_limit_per_query: int = 5,
        state_size: int = 200,
    ) -> None:
        self.client = client
        self.categories = categories
        self.window = window
        self.limit_per_category = limit_per_category
        self.use_rising = use_rising
        self.rising_hours = rising_hours
        self.search_queries = search_queries
        self.search_limit_per_query = search_limit_per_query
        self.state_size = state_size

    def fetch_since(self, last_seen: str | None) -> AttentionBatch:
        previous_seen = _parse_seen_state(last_seen)
        captures: list[CaptureResult] = []
        requested_categories = self.categories or (None,)

        for category in requested_categories:
            if self.use_rising:
                captures.extend(
                    article_to_capture(article)
                    for article in self.client.rising_articles(
                        category=category,
                        hours=self.rising_hours,
                        limit=self.limit_per_category,
                    )
                )
            captures.extend(
                article_to_capture(article)
                for article in self.client.list_articles(
                    category=category,
                    window=self.window,
                    limit=self.limit_per_category,
                )
            )

        for query in self.search_queries:
            captures.extend(
                tweet_to_capture(tweet)
                for tweet in self.client.search_tweets(query=query, limit=self.search_limit_per_query)
            )

        deduped = _dedupe_captures(captures)
        previous_seen_set = set(previous_seen)
        fresh = [capture for capture in deduped if capture.target_post.post_id not in previous_seen_set]
        next_seen_state = json.dumps(
            _build_next_seen_ids([capture.target_post.post_id for capture in deduped], previous_seen, self.state_size),
            ensure_ascii=False,
        )
        return AttentionBatch(
            captures=tuple(fresh),
            next_seen_state=next_seen_state,
            discovered_count=len(fresh),
        )


def article_to_capture(article: AttentionArticle) -> CaptureResult:
    account = Account(
        account_id=f"attentionvc:{article.author_handle}",
        platform="x",
        handle=article.author_handle,
        display_name=article.author_name,
    )
    text = build_article_text(article)
    post = Post(
        post_id=article.tweet_id,
        account_id=account.account_id,
        url=article.url,
        created_at=article.published_at,
        captured_at=utc_now(),
        text_exact=text,
        text_normalized=text,
        post_type="original",
        track=_map_category_to_track(article.category),
        conversation_id=article.tweet_id,
        lang=article.langs[0] if article.langs else None,
        likes=article.likes,
        retweets=article.retweets,
        replies=article.replies,
        views=article.views,
    )
    return CaptureResult(target_account=account, target_post=post)


def tweet_to_capture(tweet: AttentionTweet) -> CaptureResult:
    account = Account(
        account_id=f"attentionvc:{tweet.author_handle}",
        platform="x",
        handle=tweet.author_handle,
        display_name=tweet.author_name,
    )
    text = tweet.text.strip()
    post = Post(
        post_id=tweet.tweet_id,
        account_id=account.account_id,
        url=tweet.url,
        created_at=tweet.published_at,
        captured_at=utc_now(),
        text_exact=text,
        text_normalized=text,
        post_type="original",
        conversation_id=tweet.conversation_id or tweet.tweet_id,
        lang=tweet.lang,
        likes=tweet.likes,
        retweets=tweet.retweets,
        replies=tweet.replies,
        views=tweet.views,
    )
    return CaptureResult(target_account=account, target_post=post)


def build_article_text(article: AttentionArticle) -> str:
    parts = [article.title.strip(), article.preview_text.strip()]
    if article.trending_topics:
        parts.append("Topics: " + ", ".join(article.trending_topics[:5]))
    return "\n\n".join(part for part in parts if part)


def build_search_query(text: str) -> str:
    first_line = text.strip().splitlines()[0]
    stripped = re.sub(r"https?://\S+", "", first_line)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    words = stripped.split(" ")
    if len(words) > 10:
        stripped = " ".join(words[:10])
    return stripped[:80]


def _parse_articles(items: Iterable[Mapping[str, Any]]) -> list[AttentionArticle]:
    articles: list[AttentionArticle] = []
    for item in items:
        author = item.get("author", {})
        metrics = item.get("metrics", {})
        momentum = item.get("momentum", {})
        articles.append(
            AttentionArticle(
                tweet_id=str(item["tweetId"]),
                title=str(item.get("title", "")).strip(),
                preview_text=str(item.get("previewText", "")).strip(),
                url=str(item.get("url", "")).strip(),
                published_at=_parse_datetime(item.get("publishedAt")),
                author_handle=str(author.get("handle", "")).strip(),
                author_name=str(author.get("name", "")).strip(),
                author_followers=int(author.get("followers", 0) or 0),
                author_is_blue_verified=bool(author.get("isBlueVerified", False)),
                views=int(metrics.get("views", 0) or 0),
                likes=int(metrics.get("likes", 0) or 0),
                retweets=int(metrics.get("retweets", 0) or 0),
                replies=int(metrics.get("replies", 0) or 0),
                quotes=int(metrics.get("quotes", 0) or 0),
                bookmarks=int(metrics.get("bookmarks", 0) or 0),
                category=str(item["category"]).strip() if item.get("category") else None,
                langs=tuple(str(lang) for lang in item.get("langs", ()) if str(lang).strip()),
                trending_topics=tuple(
                    str(topic) for topic in (item.get("trendingTopics") or item.get("tags") or ()) if str(topic).strip()
                ),
                velocity_per_hour=float(momentum.get("velocityPerHour")) if momentum.get("velocityPerHour") is not None else None,
            )
        )
    return articles


def _parse_topics(items: Iterable[Mapping[str, Any]]) -> list[AttentionTopic]:
    topics: list[AttentionTopic] = []
    for item in items:
        topics.append(
            AttentionTopic(
                slug=str(item.get("slug", "")).strip(),
                name=str(item.get("name", "")).strip(),
                article_count=int(item.get("articleCount", 0) or 0),
                total_views=int(item.get("totalViews", 0) or 0),
            )
        )
    return [topic for topic in topics if topic.slug or topic.name]


def _parse_tweets(items: Iterable[Mapping[str, Any]]) -> list[AttentionTweet]:
    tweets: list[AttentionTweet] = []
    for item in items:
        author = item.get("author", {})
        tweets.append(
            AttentionTweet(
                tweet_id=str(item.get("id", "")).strip(),
                text=str(item.get("text", "")).strip(),
                url=str(item.get("url") or item.get("twitterUrl") or "").strip(),
                published_at=_parse_datetime(item.get("createdAt")),
                author_handle=str(author.get("userName") or author.get("handle") or "").strip(),
                author_name=str(author.get("name", "")).strip(),
                author_followers=int(author.get("followers", 0) or 0),
                author_is_blue_verified=bool(author.get("isBlueVerified", False)),
                views=int(item.get("viewCount", 0) or 0),
                likes=int(item.get("likeCount", 0) or 0),
                retweets=int(item.get("retweetCount", 0) or 0),
                replies=int(item.get("replyCount", 0) or 0),
                quotes=int(item.get("quoteCount", 0) or 0),
                bookmarks=int(item.get("bookmarkCount", 0) or 0),
                lang=str(item.get("lang") or "").strip() or None,
                conversation_id=str(item.get("conversationId") or item.get("id") or "").strip() or None,
            )
        )
    return [tweet for tweet in tweets if tweet.tweet_id and tweet.url]


def _parse_datetime(value: Any) -> datetime:
    if not value:
        return utc_now()
    text = str(value)
    if len(text) >= 10 and text[4:5] == "-" and text[7:8] == "-":
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    return parsedate_to_datetime(text)


def _map_category_to_track(category: str | None) -> str | None:
    if category == "ai":
        return "AI"
    if category == "crypto":
        return "Crypto"
    return None


def _dedupe_captures(captures: Iterable[CaptureResult]) -> list[CaptureResult]:
    seen: set[str] = set()
    deduped: list[CaptureResult] = []
    for capture in captures:
        tweet_id = capture.target_post.post_id
        if tweet_id in seen:
            continue
        seen.add(tweet_id)
        deduped.append(capture)
    return deduped


def _parse_seen_state(last_seen: str | None) -> list[str]:
    if not last_seen:
        return []
    try:
        loaded = json.loads(last_seen)
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return [str(item) for item in loaded if str(item).strip()]


def _build_next_seen_ids(current_ids: list[str], previous_seen: list[str], state_size: int) -> list[str]:
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
