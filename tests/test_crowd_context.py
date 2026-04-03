from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from twitter_ops_agent.discovery.attentionvc import AttentionTweet
from twitter_ops_agent.research.crowd_context import CrowdContextService, classify_signal_emotion, heuristic_crowd_summary


def _tweet(tweet_id: str, *, text: str, likes: int = 0, replies: int = 0, views: int = 0) -> AttentionTweet:
    return AttentionTweet(
        tweet_id=tweet_id,
        text=text,
        url=f"https://x.com/example/status/{tweet_id}",
        published_at=datetime(2026, 3, 31, tzinfo=timezone.utc),
        author_handle=f"author_{tweet_id}",
        author_name=f"Author {tweet_id}",
        author_followers=100,
        author_is_blue_verified=False,
        views=views,
        likes=likes,
        retweets=0,
        replies=replies,
        quotes=0,
        bookmarks=0,
        lang="en",
        conversation_id=tweet_id,
    )


@dataclass
class StubClient:
    thread_items: list[AttentionTweet]
    reply_items: list[AttentionTweet]
    search_items: list[AttentionTweet]

    def tweet_thread(self, *, tweet_id: str) -> list[AttentionTweet]:
        return list(self.thread_items)

    def tweet_replies(self, *, tweet_id: str, limit: int = 20) -> list[AttentionTweet]:
        return list(self.reply_items)[:limit]

    def search_tweets(self, *, query: str, limit: int = 20) -> list[AttentionTweet]:
        return list(self.search_items)[:limit]


def test_heuristic_crowd_summary_prefers_skeptical_language_when_present():
    signals = [
        _tweet("r1", text="This looks fake and people should question the numbers.", likes=50, replies=10, views=2000),
        _tweet("r2", text="Huge risk if this does not convert into real usage.", likes=30, replies=4, views=1000),
    ]

    summary = heuristic_crowd_summary(
        seed_text="some seed",
        thread=[],
        signals=[
            type("Signal", (), {
                "tweet_id": item.tweet_id,
                "author_handle": item.author_handle,
                "author_name": item.author_name,
                "text": item.text,
                "url": item.url,
                "likes": item.likes,
                "replies": item.replies,
                "views": item.views,
                "bookmarks": item.bookmarks,
                "signal_score": 10.0,
                "source_type": "reply",
            })()
            for item in signals
        ],
        source_label="评论区",
    )

    assert "质疑" in summary.sentiment_summary or "求证" in summary.sentiment_summary
    assert summary.key_points
    assert summary.suggested_angles


def test_crowd_context_service_falls_back_to_search_discussion_when_replies_are_empty():
    service = CrowdContextService(
        client=StubClient(
            thread_items=[_tweet("seed", text="seed text", likes=100, replies=20, views=5000)],
            reply_items=[],
            search_items=[
                _tweet("s1", text="Anthropic shipped something important, but the real story is distribution.", likes=80, replies=9, views=9000),
                _tweet("s2", text="Anthropic important dev workflows will change faster than most people expect.", likes=50, replies=6, views=7000),
            ],
        ),
        reply_sample_limit=10,
        top_signal_count=2,
        summarizer=None,
    )

    summary = service.build(tweet_id="seed", seed_text="Anthropic shipped something important for dev workflows.")

    assert summary.source_label == "相关讨论"
    assert len(summary.top_signals) == 2
    assert summary.top_signals[0].source_type == "discussion"


def test_crowd_context_service_supplements_sparse_replies_with_thread_and_related_discussion():
    service = CrowdContextService(
        client=StubClient(
            thread_items=[
                _tweet("seed", text="seed text that is long enough to be ignored as the source seed", likes=100, replies=20, views=5000),
                _tweet("t1", text="Thread follow-up adds useful context about why the roadmap credibility matters here.", likes=1, replies=0, views=120),
            ],
            reply_items=[
                _tweet("r1", text="Reply one says trust is the real issue, not the announcement itself.", likes=0, replies=0, views=80),
                _tweet("r2", text="Reply two says the launch sounds exciting if the team can actually ship on time.", likes=0, replies=0, views=70),
            ],
            search_items=[
                _tweet("s1", text="Launch roadmap trust discussion says the market will care more about retention than theatrics.", likes=0, replies=0, views=400),
                _tweet("s2", text="Launch roadmap trust discussion says the main fear is another delay damaging community trust even more.", likes=0, replies=0, views=300),
                _tweet("s3", text="Launch roadmap trust discussion says curious builders still want proof instead of slogans in the comments.", likes=0, replies=0, views=200),
            ],
        ),
        reply_sample_limit=10,
        top_signal_count=5,
        summarizer=None,
    )

    summary = service.build(tweet_id="seed", seed_text="Launch thread about roadmap credibility and trust.")

    assert len(summary.top_signals) >= 5
    assert {signal.source_type for signal in summary.top_signals} == {"reply", "thread", "discussion"}


def test_crowd_context_service_keeps_extra_candidates_for_downstream_filtering():
    reply_items = [
        _tweet(
            f"r{index}",
            text=f"Reply {index} contains enough detail to survive ranking and downstream filtering for the final note.",
            likes=0,
            replies=0,
            views=200 - index,
        )
        for index in range(12)
    ]
    service = CrowdContextService(
        client=StubClient(
            thread_items=[_tweet("seed", text="seed text that is long enough to be ignored as the source seed", likes=100, replies=20, views=5000)],
            reply_items=reply_items,
            search_items=[],
        ),
        reply_sample_limit=20,
        top_signal_count=5,
        summarizer=None,
    )

    summary = service.build(tweet_id="seed", seed_text="Seed topic text.")

    assert len(summary.top_signals) == 12


def test_classify_signal_emotion_detects_crypto_bearish_fud_language():
    text = (
        "同意以下6点：CVDD 有参考，但我个人觉得最大跌幅 30% 这个可能不一定，"
        "可以临近 20% 左右开始分批买。底部区域 45000-55000，时间 2-3 个月，当前策略：等待 + 轻仓。"
    )

    assert classify_signal_emotion(text) == "担忧/风险"
