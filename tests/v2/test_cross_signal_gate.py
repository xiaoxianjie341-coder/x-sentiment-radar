from __future__ import annotations

from datetime import datetime, timezone

from twitter_ops_agent.discovery.attentionvc import AttentionTweet
from twitter_ops_agent.discovery.polymarket import PolymarketCandidate
from twitter_ops_agent.v2.agents.cross_signal_gate import CrossSignalGate, build_topic_queries


def _candidate(title: str = "Will KitKat issue a statement about the heist by April 8, 2026?") -> PolymarketCandidate:
    return PolymarketCandidate(
        market_id="market-1",
        title=title,
        slug="kitkat-heist-response",
        market_url="https://polymarket.com/event/kitkat-heist-response",
        category_label="Culture",
        category_slug="pop-culture",
        source_label="breaking",
    )


def _tweet(
    tweet_id: str,
    *,
    author: str,
    text: str,
    likes: int,
    retweets: int,
    replies: int,
    quotes: int,
    views: int,
) -> AttentionTweet:
    return AttentionTweet(
        tweet_id=tweet_id,
        text=text,
        url=f"https://x.com/{author}/status/{tweet_id}",
        published_at=datetime(2026, 4, 7, tzinfo=timezone.utc),
        author_handle=author,
        author_name=author,
        author_followers=1000,
        author_is_blue_verified=False,
        views=views,
        likes=likes,
        retweets=retweets,
        replies=replies,
        quotes=quotes,
        bookmarks=0,
        lang="en",
        conversation_id=tweet_id,
    )


class StubSearchClient:
    def __init__(self, results: dict[str, list[AttentionTweet]]) -> None:
        self.results = results
        self.calls: list[tuple[str, int]] = []

    def search_tweets(self, *, query: str, limit: int = 20) -> list[AttentionTweet]:
        self.calls.append((query, limit))
        return list(self.results.get(query, ()))[:limit]


def test_build_topic_queries_produces_short_searchable_queries():
    queries = build_topic_queries(_candidate())

    assert 1 <= len(queries) <= 3
    assert any("kitkat" in query.lower() for query in queries)
    assert all("april" not in query.lower() for query in queries)
    assert all(not query.lower().startswith("will ") for query in queries)


def test_cross_signal_gate_passes_when_topic_has_multi_post_spread():
    posts = [
        _tweet(
            "1",
            author="brandwatch",
            text="KitKat heist is becoming a brand meme moment already.",
            likes=800,
            retweets=120,
            replies=80,
            quotes=30,
            views=15000,
        ),
        _tweet(
            "2",
            author="adnews",
            text="Everyone is remixing the KitKat heist into marketing commentary.",
            likes=400,
            retweets=90,
            replies=40,
            quotes=20,
            views=9000,
        ),
        _tweet(
            "3",
            author="creatorloop",
            text="The KitKat story is spreading because it is equal parts scandal and content bait.",
            likes=250,
            retweets=40,
            replies=25,
            quotes=15,
            views=5000,
        ),
        _tweet(
            "4",
            author="creatorloop",
            text="KitKat should answer fast before this meme wave hardens.",
            likes=150,
            retweets=15,
            replies=10,
            quotes=4,
            views=2200,
        ),
    ]
    client = StubSearchClient({"kitkat heist": posts})
    gate = CrossSignalGate(client=client, min_posts=3, min_accounts=2, search_limit=10)

    alert = gate.evaluate(_candidate(), queries=("kitkat heist",))

    assert alert is not None
    assert alert.verification_passed is True
    assert alert.distinct_post_count == 4
    assert alert.distinct_account_count == 3
    assert [post.tweet_id for post in alert.top_posts] == ["1", "2", "3", "4"]
    assert "KitKat heist" in alert.angle_summary


def test_cross_signal_gate_fails_when_topic_is_single_account_noise():
    posts = [
        _tweet(
            "1",
            author="onlyone",
            text="OpenAI rumor rumor rumor",
            likes=30,
            retweets=4,
            replies=2,
            quotes=0,
            views=600,
        ),
        _tweet(
            "2",
            author="onlyone",
            text="OpenAI rumor follow-up thread",
            likes=20,
            retweets=2,
            replies=1,
            quotes=0,
            views=400,
        ),
    ]
    client = StubSearchClient({"openai release": posts})
    gate = CrossSignalGate(client=client, min_posts=3, min_accounts=2, search_limit=10)

    alert = gate.evaluate(
        _candidate("Will OpenAI release GPT-6 this week?"),
        queries=("openai release",),
    )

    assert alert is None
