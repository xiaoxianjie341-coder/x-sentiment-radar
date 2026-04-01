from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from twitter_ops_agent.discovery.attentionvc import (
    AttentionArticle,
    AttentionTweet,
    AttentionVCArticleClient,
    AttentionVCDiscoveryService,
    AttentionTopic,
    _parse_datetime,
    article_to_capture,
    tweet_to_capture,
)


def _article(tweet_id: str, *, category: str = "ai", title: str | None = None, preview: str | None = None) -> AttentionArticle:
    return AttentionArticle(
        tweet_id=tweet_id,
        title=title or f"title-{tweet_id}",
        preview_text=preview or f"preview-{tweet_id}",
        url=f"https://x.com/example/status/{tweet_id}",
        published_at=datetime(2026, 3, 31, tzinfo=timezone.utc),
        author_handle=f"author_{tweet_id}",
        author_name=f"Author {tweet_id}",
        author_followers=1234,
        author_is_blue_verified=True,
        views=1000,
        likes=100,
        retweets=10,
        replies=5,
        quotes=1,
        bookmarks=9,
        category=category,
        langs=("en",),
        trending_topics=("agents",),
        velocity_per_hour=500.0,
    )


@dataclass
class StubAttentionClient:
    rising_by_category: dict[str | None, list[AttentionArticle]] = field(default_factory=dict)
    browse_by_category: dict[str | None, list[AttentionArticle]] = field(default_factory=dict)
    search_by_query: dict[str, list[AttentionTweet]] = field(default_factory=dict)
    calls: list[tuple[str, str | None]] = field(default_factory=list)

    def rising_articles(self, *, category: str | None, hours: int, limit: int) -> list[AttentionArticle]:
        self.calls.append(("rising", category))
        return list(self.rising_by_category.get(category, []))[:limit]

    def list_articles(self, *, category: str | None, window: str, limit: int) -> list[AttentionArticle]:
        self.calls.append(("articles", category))
        return list(self.browse_by_category.get(category, []))[:limit]

    def search_tweets(self, *, query: str, limit: int) -> list[AttentionTweet]:
        self.calls.append(("search", query))
        return list(self.search_by_query.get(query, []))[:limit]


def _tweet(tweet_id: str, *, text: str | None = None) -> AttentionTweet:
    return AttentionTweet(
        tweet_id=tweet_id,
        text=text or f"tweet-text-{tweet_id}",
        url=f"https://x.com/example/status/{tweet_id}",
        published_at=datetime(2026, 3, 31, tzinfo=timezone.utc),
        author_handle=f"tweet_author_{tweet_id}",
        author_name=f"Tweet Author {tweet_id}",
        author_followers=999,
        author_is_blue_verified=False,
        views=123,
        likes=45,
        retweets=6,
        replies=7,
        quotes=0,
        bookmarks=3,
        lang="en",
        conversation_id=tweet_id,
    )


def test_article_to_capture_uses_title_and_preview_as_post_text():
    capture = article_to_capture(_article("tweet-1", category="crypto"))

    assert capture.target_post.post_id == "tweet-1"
    assert capture.target_post.track == "Crypto"
    assert capture.target_post.url == "https://x.com/example/status/tweet-1"
    assert "title-tweet-1" in capture.target_post.text_exact
    assert "preview-tweet-1" in capture.target_post.text_exact
    assert capture.target_post.views == 1000
    assert capture.target_account.handle == "author_tweet-1"


def test_attentionvc_fetch_since_filters_seen_ids_and_updates_state():
    client = StubAttentionClient(
        browse_by_category={
            "ai": [_article("tweet-1"), _article("tweet-2")],
            "crypto": [_article("tweet-3", category="crypto")],
        }
    )
    service = AttentionVCDiscoveryService(
        client=client,
        categories=("ai", "crypto"),
        window="7d",
        limit_per_category=5,
        use_rising=False,
        state_size=10,
    )

    batch = service.fetch_since(last_seen=json.dumps(["tweet-1"]))

    assert batch.discovered_count == 2
    assert [capture.target_post.post_id for capture in batch.captures] == ["tweet-2", "tweet-3"]
    assert json.loads(batch.next_seen_state)[:3] == ["tweet-1", "tweet-2", "tweet-3"]
    assert client.calls == [("articles", "ai"), ("articles", "crypto")]


def test_attentionvc_fetch_since_can_merge_rising_and_articles_without_duplicates():
    shared = _article("tweet-1")
    client = StubAttentionClient(
        rising_by_category={"ai": [shared]},
        browse_by_category={"ai": [shared, _article("tweet-2")]},
    )
    service = AttentionVCDiscoveryService(
        client=client,
        categories=("ai",),
        window="7d",
        limit_per_category=5,
        use_rising=True,
        rising_hours=24,
        state_size=10,
    )

    batch = service.fetch_since(last_seen=None)

    assert batch.discovered_count == 2
    assert [capture.target_post.post_id for capture in batch.captures] == ["tweet-1", "tweet-2"]
    assert client.calls == [("rising", "ai"), ("articles", "ai")]


def test_tweet_to_capture_keeps_regular_tweet_text():
    capture = tweet_to_capture(_tweet("tweet-9", text="plain tweet content"))

    assert capture.target_post.post_id == "tweet-9"
    assert capture.target_post.text_exact == "plain tweet content"
    assert capture.target_post.url == "https://x.com/example/status/tweet-9"


def test_attentionvc_fetch_since_can_include_search_queries_for_normal_tweets():
    client = StubAttentionClient(
        browse_by_category={"ai": [_article("article-1")]},
        search_by_query={"anthropic": [_tweet("tweet-1"), _tweet("tweet-2")]},
    )
    service = AttentionVCDiscoveryService(
        client=client,
        categories=("ai",),
        search_queries=("anthropic",),
        search_limit_per_query=5,
        window="7d",
        limit_per_category=5,
        use_rising=False,
        state_size=10,
    )

    batch = service.fetch_since(last_seen=None)

    assert batch.discovered_count == 3
    assert [capture.target_post.post_id for capture in batch.captures] == ["article-1", "tweet-1", "tweet-2"]
    assert client.calls == [("articles", "ai"), ("search", "anthropic")]


def test_parse_datetime_supports_attentionvc_twitter_style_timestamp():
    parsed = _parse_datetime("Tue Mar 31 09:48:36 +0000 2026")

    assert parsed.year == 2026
    assert parsed.month == 3
    assert parsed.day == 31


def test_tweet_replies_prefers_primary_endpoint_before_v2_fallback():
    class StubClient(AttentionVCArticleClient):
        def __init__(self):
            self.calls = []
            self.api_key = "test"
            self.base_url = "https://api.attentionvc.ai"
            self.timeout = 20.0

        def _get_json(self, path, params):
            self.calls.append(path)
            if path == "/v1/x/tweet/replies":
                return {
                    "tweets": [
                        {
                            "id": "reply-1",
                            "text": "real reply",
                            "createdAt": "Tue Mar 31 09:48:36 +0000 2026",
                            "author": {"userName": "replyguy", "name": "Reply Guy", "followers": 10},
                            "likeCount": 5,
                            "replyCount": 2,
                            "viewCount": 100,
                            "bookmarkCount": 1,
                            "quoteCount": 0,
                            "url": "https://x.com/replyguy/status/reply-1",
                        }
                    ]
                }
            if path == "/v1/x/tweet/replies/v2":
                return {"tweets": []}
            raise AssertionError(path)

    client = StubClient()
    replies = client.tweet_replies(tweet_id="seed", limit=5)

    assert len(replies) == 1
    assert replies[0].tweet_id == "reply-1"
    assert client.calls == ["/v1/x/tweet/replies"]


def test_tweet_replies_paginates_until_limit():
    class StubClient(AttentionVCArticleClient):
        def __init__(self):
            self.calls = []
            self.api_key = "test"
            self.base_url = "https://api.attentionvc.ai"
            self.timeout = 20.0

        def _get_json(self, path, params):
            self.calls.append((path, dict(params)))
            if path != "/v1/x/tweet/replies":
                return {"tweets": []}
            if "cursor" not in params:
                return {
                    "tweets": [
                        {
                            "id": "reply-1",
                            "text": "first page reply",
                            "createdAt": "Tue Mar 31 09:48:36 +0000 2026",
                            "author": {"userName": "reply1", "name": "Reply 1", "followers": 10},
                            "likeCount": 5,
                            "replyCount": 2,
                            "viewCount": 100,
                            "bookmarkCount": 1,
                            "quoteCount": 0,
                            "url": "https://x.com/reply1/status/reply-1",
                        }
                    ],
                    "has_next_page": True,
                    "next_cursor": "cursor-2",
                }
            return {
                "tweets": [
                    {
                        "id": "reply-2",
                        "text": "second page reply",
                        "createdAt": "Tue Mar 31 09:48:36 +0000 2026",
                        "author": {"userName": "reply2", "name": "Reply 2", "followers": 10},
                        "likeCount": 3,
                        "replyCount": 1,
                        "viewCount": 50,
                        "bookmarkCount": 0,
                        "quoteCount": 0,
                        "url": "https://x.com/reply2/status/reply-2",
                    }
                ],
                "has_next_page": False,
                "next_cursor": None,
            }

    client = StubClient()
    replies = client.tweet_replies(tweet_id="seed", limit=2)

    assert [reply.tweet_id for reply in replies] == ["reply-1", "reply-2"]
    assert client.calls == [
        ("/v1/x/tweet/replies", {"tweetId": "seed"}),
        ("/v1/x/tweet/replies", {"tweetId": "seed", "cursor": "cursor-2"}),
    ]


def test_trending_topics_parses_topic_entries():
    class StubClient(AttentionVCArticleClient):
        def __init__(self):
            self.api_key = "test"
            self.base_url = "https://api.attentionvc.ai"
            self.timeout = 20.0

        def _get_json(self, path, params):
            assert path == "/v1/x/trending"
            return {
                "topics": [
                    {"slug": "anthropic", "name": "Anthropic", "articleCount": 12, "totalViews": 999999},
                ]
            }

    client = StubClient()
    topics = client.trending_topics(window="7d")

    assert topics == [AttentionTopic(slug="anthropic", name="Anthropic", article_count=12, total_views=999999)]
