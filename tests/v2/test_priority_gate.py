from __future__ import annotations

from twitter_ops_agent.v2.agents.priority_gate import PriorityGateAgent
from twitter_ops_agent.v2.contracts import HydratedSeed, ScoutSeed


def _seed(tweet_id: str, *, views: int, likes: int, replies: int) -> HydratedSeed:
    return HydratedSeed(
        seed=ScoutSeed(
            seed_id=f"seed:{tweet_id}",
            source_kind="tweet",
            query="anthropic",
            tweet_id=tweet_id,
            url=f"https://x.com/example/status/{tweet_id}",
            text="Anthropic shipped something important.",
            title="Anthropic shipped something important.",
            track="AI",
            author_handle="anthropicnews",
            views=views,
            likes=likes,
            replies=replies,
            velocity_hint=0.0,
        ),
        event_id=f"event:{tweet_id}",
        source_url=f"https://x.com/example/status/{tweet_id}",
        source_text="Anthropic shipped something important.",
        track="AI",
    )


def test_priority_gate_prefers_growth_over_static_popularity():
    gate = PriorityGateAgent(daily_budget=2)
    stable_big = _seed("old-big", views=100000, likes=500, replies=80)
    rising_mid = _seed("rising", views=15000, likes=120, replies=40)

    ranked = gate.run(
        [stable_big, rising_mid],
        previous_snapshots={
            "old-big": {"views": 99000, "likes": 495, "replies": 79},
            "rising": {"views": 5000, "likes": 40, "replies": 10},
        },
    )

    assert ranked[0].seed.tweet_id == "rising"
