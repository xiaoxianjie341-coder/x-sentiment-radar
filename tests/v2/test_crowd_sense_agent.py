from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from twitter_ops_agent.domain.models import CrowdSignal, CrowdSummary
from twitter_ops_agent.v2.agents.crowd_sense import CrowdSenseAgent
from twitter_ops_agent.v2.contracts import HydratedSeed, ScoutSeed


@dataclass
class StubCrowdContext:
    def build(self, *, tweet_id: str, seed_text: str):
        return CrowdSummary(
            sentiment_summary="评论区偏质疑。",
            key_points=("很多人关心这是不是事故。",),
            suggested_angles=("可以从信任危机切。",),
            top_signals=(
                CrowdSignal(
                    tweet_id="1",
                    author_handle="threadreaderapp",
                    author_name="threadreaderapp",
                    text="@threadreaderapp unroll",
                    url="https://x.com/threadreaderapp/status/1",
                    likes=1,
                    replies=1,
                    views=999,
                    bookmarks=0,
                    signal_score=20.0,
                    source_type="reply",
                ),
                CrowdSignal(
                    tweet_id="2",
                    author_handle="useful_builder",
                    author_name="Useful Builder",
                    text="The real issue is whether devs now trust the product less after this leak.",
                    url="https://x.com/useful_builder/status/2",
                    likes=12,
                    replies=4,
                    views=800,
                    bookmarks=1,
                    signal_score=80.0,
                    source_type="reply",
                ),
            ),
            source_label="评论区",
        )


def test_crowd_sense_agent_filters_noise_signals():
    seed = HydratedSeed(
        seed=ScoutSeed(
            seed_id="seed-1",
            source_kind="tweet",
            query="anthropic",
            tweet_id="tweet-1",
            url="https://x.com/example/status/1",
            text="Anthropic shipped something important for agents.",
            title="Anthropic shipped something important for agents.",
            track="AI",
            author_handle="anthropicnews",
            views=10000,
            replies=100,
            likes=200,
            velocity_hint=100.0,
        ),
        event_id="event-1",
        source_url="https://x.com/example/status/1",
        source_text="Anthropic shipped something important for agents.",
        track="AI",
    )

    agent = CrowdSenseAgent(
        crowd_context=StubCrowdContext(),
        signal_min_views=50,
        signal_min_likes=1,
        signal_min_replies=1,
    )

    result = agent.run(seed)

    assert len(result.top_signals) == 1
    assert result.top_signals[0].author_handle == "useful_builder"
