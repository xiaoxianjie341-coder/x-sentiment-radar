from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from twitter_ops_agent.discovery.attentionvc import AttentionArticle, AttentionTweet
from twitter_ops_agent.v2.agents.topic_scout import TopicScoutAgent


def _article(tweet_id: str, *, category: str = "ai", title: str | None = None) -> AttentionArticle:
    return AttentionArticle(
        tweet_id=tweet_id,
        title=title or f"title-{tweet_id}",
        preview_text=f"preview-{tweet_id}",
        url=f"https://x.com/example/status/{tweet_id}",
        published_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        author_handle=f"author_{tweet_id}",
        author_name=f"Author {tweet_id}",
        author_followers=1000,
        author_is_blue_verified=True,
        views=5000,
        likes=100,
        retweets=20,
        replies=30,
        quotes=3,
        bookmarks=10,
        category=category,
        langs=("en",),
        trending_topics=("agents",),
        velocity_per_hour=250.0,
    )


def _tweet(tweet_id: str, *, text: str) -> AttentionTweet:
    return AttentionTweet(
        tweet_id=tweet_id,
        text=text,
        url=f"https://x.com/example/status/{tweet_id}",
        published_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        author_handle=f"tweet_author_{tweet_id}",
        author_name=f"Tweet Author {tweet_id}",
        author_followers=500,
        author_is_blue_verified=False,
        views=3000,
        likes=40,
        retweets=5,
        replies=12,
        quotes=0,
        bookmarks=2,
        lang="en",
        conversation_id=tweet_id,
    )


@dataclass
class StubAttentionClient:
    browse_by_category: dict[str | None, list[AttentionArticle]] = field(default_factory=dict)
    search_by_query: dict[str, list[AttentionTweet]] = field(default_factory=dict)
    trending_topics_items: list[object] = field(default_factory=list)
    insights_by_category: dict[str, dict] = field(default_factory=dict)

    def list_articles(self, *, category: str | None, window: str, limit: int):
        return list(self.browse_by_category.get(category, []))[:limit]

    def search_tweets(self, *, query: str, limit: int):
        return list(self.search_by_query.get(query, []))[:limit]

    def trending_topics(self, *, window: str = "7d"):
        return list(self.trending_topics_items)

    def category_insights(self, *, category: str, window: str = "7d"):
        return dict(self.insights_by_category.get(category, {}))


def test_topic_scout_merges_articles_and_keyword_tweets_without_duplicates():
    scout = TopicScoutAgent(
        client=StubAttentionClient(
            browse_by_category={"ai": [_article("a1")]},
            search_by_query={
                "anthropic": [
                    _tweet("t1", text="Anthropic shipped something important for agents."),
                    _tweet("t2", text="Anthropic discussion keeps growing among builders."),
                ]
            },
        ),
        categories=("ai",),
        article_window="7d",
        article_limit_per_category=5,
        search_queries=("anthropic",),
        search_limit_per_query=5,
    )

    result = scout.fetch_since(last_seen=None)
    seeds = result.seeds

    assert [seed.tweet_id for seed in seeds] == ["a1", "t1", "t2"]
    assert seeds[0].source_kind == "article"
    assert seeds[1].source_kind == "tweet"


def test_topic_scout_can_run_in_tweets_only_mode():
    scout = TopicScoutAgent(
        client=StubAttentionClient(
            browse_by_category={"ai": [_article("a1")]},
            search_by_query={"anthropic": [_tweet("t1", text="Anthropic shipped something important for agents.")]},
        ),
        categories=("ai",),
        article_window="7d",
        article_limit_per_category=5,
        search_queries=("anthropic",),
        search_limit_per_query=5,
        source_mode="tweets_only",
    )

    result = scout.fetch_since(last_seen=None)

    assert [seed.tweet_id for seed in result.seeds] == ["t1"]


def test_topic_scout_can_apply_different_thresholds_to_articles_and_tweets():
    scout = TopicScoutAgent(
        client=StubAttentionClient(
            browse_by_category={"ai": [_article("a1")]},
            search_by_query={"anthropic": [_tweet("t1", text="Anthropic shipped something important for agents.")]},
        ),
        categories=("ai",),
        article_window="7d",
        article_limit_per_category=5,
        search_queries=("anthropic",),
        search_limit_per_query=5,
        source_mode="mixed",
        article_min_views=10000,
        article_min_likes=200,
        article_min_replies=50,
        tweet_min_views=100,
        tweet_min_likes=10,
        tweet_min_replies=3,
    )

    result = scout.fetch_since(last_seen=None)

    assert [seed.tweet_id for seed in result.seeds] == ["t1"]


def test_topic_scout_can_expand_queries_from_trending_and_category_insights():
    @dataclass
    class Topic:
        slug: str
        name: str
        article_count: int
        total_views: int

    client = StubAttentionClient(
        browse_by_category={"ai": [_article("a1", title="Anthropic leaked source maps")]},
        search_by_query={
            "Anthropic": [_tweet("t1", text="Anthropic discussion keeps growing among builders.")],
            "Anthropic leaked source maps": [_tweet("t2", text="Source map leak becomes a bigger trust debate.")],
        },
        trending_topics_items=[Topic(slug="anthropic", name="Anthropic", article_count=10, total_views=99999)],
        insights_by_category={
            "ai": {
                "topArticles": [
                    {"title": "Anthropic leaked source maps", "author": "dashen_wang"}
                ]
            }
        },
    )
    scout = TopicScoutAgent(
        client=client,
        categories=("ai",),
        article_window="7d",
        article_limit_per_category=5,
        search_queries=(),
        search_limit_per_query=5,
        source_mode="tweets_only",
        topic_query_limit=4,
    )

    result = scout.fetch_since(last_seen=None)

    assert [seed.tweet_id for seed in result.seeds] == ["t1", "t2"]
