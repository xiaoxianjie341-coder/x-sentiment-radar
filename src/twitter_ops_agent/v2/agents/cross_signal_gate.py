from __future__ import annotations

from dataclasses import dataclass
import re

from twitter_ops_agent.discovery.attentionvc import AttentionTweet
from twitter_ops_agent.discovery.polymarket import PolymarketCandidate
from twitter_ops_agent.domain.models import CrossSignalAlert, CrossSignalPost


_LEADING_QUESTION_RE = re.compile(r"^(will|would|did|does|is|are|can|could|should|what|who|how)\s+", re.I)
_TRAILING_TIME_RE = re.compile(
    r"\b(by|before|after|in|on)\s+(january|february|march|april|may|june|july|august|september|october|november|december|\d{4}).*$",
    re.I,
)
_NON_WORD_RE = re.compile(r"[^0-9A-Za-z]+")
_STOPWORDS = {
    "the",
    "this",
    "that",
    "about",
    "statement",
    "issue",
    "release",
    "major",
    "week",
    "month",
    "year",
    "after",
    "before",
    "about",
}


@dataclass(slots=True)
class CrossSignalGate:
    client: object
    min_posts: int = 3
    min_accounts: int = 2
    search_limit: int = 20
    top_post_limit: int = 5

    def evaluate(
        self,
        candidate: PolymarketCandidate,
        *,
        queries: tuple[str, ...] | None = None,
    ) -> CrossSignalAlert | None:
        resolved_queries = queries or build_topic_queries(candidate)
        ranked = _collect_ranked_posts(self.client, resolved_queries, limit=self.search_limit)
        if len(ranked) < self.min_posts:
            return None

        distinct_accounts = len({post.author_handle.lower() for post in ranked if post.author_handle})
        if distinct_accounts < self.min_accounts:
            return None

        top_posts = tuple(ranked[: self.top_post_limit])
        return CrossSignalAlert(
            topic=_topic_label(candidate),
            market_title=candidate.title,
            market_url=candidate.market_url,
            source_label=candidate.source_label,
            queries=tuple(resolved_queries),
            top_posts=top_posts,
            angle_summary=_summarize_angle(top_posts),
            distinct_post_count=len(ranked),
            distinct_account_count=distinct_accounts,
            verification_passed=True,
        )


def build_topic_queries(candidate: PolymarketCandidate, *, limit: int = 3) -> tuple[str, ...]:
    cleaned = _LEADING_QUESTION_RE.sub("", candidate.title).strip()
    cleaned = _TRAILING_TIME_RE.sub("", cleaned).strip().strip("?").strip()
    tokens = [
        token
        for token in _NON_WORD_RE.sub(" ", cleaned).split()
        if len(token) >= 3 and token.lower() not in _STOPWORDS and not token.isdigit()
    ]
    if not tokens:
        return (candidate.slug.replace("-", " "),)

    queries: list[str] = []
    if len(tokens) >= 2:
        queries.append(" ".join(tokens[:2]))
    queries.append(tokens[0])
    if len(tokens) >= 3:
        queries.append(" ".join(tokens[:3]))

    seen: set[str] = set()
    deduped: list[str] = []
    for query in queries:
        normalized = " ".join(query.split()).strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(normalized)
        if len(deduped) >= limit:
            break
    return tuple(deduped)


def _collect_ranked_posts(client: object, queries: tuple[str, ...], *, limit: int) -> list[CrossSignalPost]:
    by_id: dict[str, CrossSignalPost] = {}
    for query in queries:
        for tweet in client.search_tweets(query=query, limit=limit):
            post = _to_cross_signal_post(tweet)
            existing = by_id.get(post.tweet_id)
            if existing is None or post.spread_score > existing.spread_score:
                by_id[post.tweet_id] = post
    return sorted(by_id.values(), key=lambda item: item.spread_score, reverse=True)


def _to_cross_signal_post(tweet: AttentionTweet) -> CrossSignalPost:
    return CrossSignalPost(
        tweet_id=tweet.tweet_id,
        author_handle=tweet.author_handle,
        text=tweet.text,
        url=tweet.url,
        likes=tweet.likes,
        retweets=tweet.retweets,
        replies=tweet.replies,
        quotes=tweet.quotes,
        views=tweet.views,
        spread_score=_spread_score(tweet),
    )


def _spread_score(tweet: AttentionTweet) -> float:
    return (
        tweet.retweets * 4
        + tweet.quotes * 5
        + tweet.replies * 2
        + tweet.likes
        + min(tweet.views / 500.0, 200.0)
    )


def _topic_label(candidate: PolymarketCandidate) -> str:
    queries = build_topic_queries(candidate, limit=1)
    if queries:
        return queries[0]
    return candidate.title


def _summarize_angle(posts: tuple[CrossSignalPost, ...]) -> str:
    if not posts:
        return "X 上还没有形成稳定角度。"
    lead = " ".join(posts[0].text.split())[:120]
    return f"X 上当前跑出来的角度更偏：{lead}"
