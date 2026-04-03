from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from twitter_ops_agent.discovery.attentionvc import AttentionTweet
from twitter_ops_agent.v2.agents.hydration_agent import HydrationAgent
from twitter_ops_agent.v2.contracts import ScoutSeed


def _seed() -> ScoutSeed:
    return ScoutSeed(
        seed_id="xhunt:1",
        source_kind="tweet",
        query="global",
        tweet_id="101",
        url="https://twitter.com/ai_writer/status/101",
        text="Anthropic snippet",
        title="Anthropic snippet",
        track="AI",
        author_handle="ai_writer",
        views=1200,
        replies=0,
        likes=30,
        velocity_hint=0.8,
    )


def _detail() -> AttentionTweet:
    return AttentionTweet(
        tweet_id="101",
        text="Anthropic shipped a longer source tweet that should replace the preview snippet.",
        url="https://x.com/ai_writer/status/101",
        published_at=datetime(2026, 4, 2, tzinfo=timezone.utc),
        author_handle="ai_writer",
        author_name="AI Writer",
        author_followers=5000,
        author_is_blue_verified=False,
        views=9500,
        likes=420,
        retweets=25,
        replies=90,
        quotes=12,
        bookmarks=8,
        lang="en",
        conversation_id="101",
    )


@dataclass
class StubRepo:
    saved: list[object]

    def save_capture_result(self, capture):
        self.saved.append(capture)

    def load_event_context(self, post_ids, conversation_ids):
        return {}


class StubEvents:
    def link_many(self, captures, event_context=None):
        items = []
        for capture in captures:
            event_link = type("EventLink", (), {"event_id": f"event:{capture.target_post.post_id}"})()
            items.append(type("LinkedCapture", (), {"event_link": event_link, "capture": capture})())
        return items

    def persist_many(self, linked):
        return None


@dataclass
class StubFetcher:
    item: AttentionTweet

    def tweet_details(self, *, tweet_id: str):
        return self.item if tweet_id == self.item.tweet_id else None


def test_hydration_agent_can_refresh_seed_with_source_fetcher_details():
    repo = StubRepo(saved=[])
    agent = HydrationAgent(
        repo=repo,
        events=StubEvents(),
        source_fetcher=StubFetcher(item=_detail()),
    )

    hydrated = agent.run([_seed()])

    assert hydrated[0].seed.text.startswith("Anthropic shipped a longer source tweet")
    assert hydrated[0].seed.views == 9500
    assert hydrated[0].seed.likes == 420
    assert hydrated[0].seed.replies == 90
    assert hydrated[0].source_url == "https://x.com/ai_writer/status/101"
    assert hydrated[0].source_text.startswith("Anthropic shipped a longer source tweet")
    assert repo.saved[0].target_post.views == 9500
