from __future__ import annotations

from dataclasses import dataclass

from twitter_ops_agent.domain.models import CrossSignalAlert, CrossSignalPost
from twitter_ops_agent.v2.cross_signal import CrossSignalOrchestrator


@dataclass
class StubScout:
    items: list[object]

    def run(self):
        return list(self.items)


@dataclass
class StubGate:
    passed_for: set[str]

    def evaluate(self, candidate):
        if candidate.slug not in self.passed_for:
            return None
        return CrossSignalAlert(
            topic=candidate.slug,
            market_title=candidate.title,
            market_url=candidate.market_url,
            source_label=candidate.source_label,
            queries=("kitkat heist",),
            top_posts=(
                CrossSignalPost(
                    tweet_id="1",
                    author_handle="brandwatch",
                    text="KitKat heist is taking over X.",
                    url="https://x.com/brandwatch/status/1",
                    likes=500,
                    retweets=80,
                    replies=40,
                    quotes=12,
                    views=10000,
                    spread_score=1024.0,
                ),
            ),
            angle_summary="X 上当前跑出来的角度更偏：KitKat heist is taking over X.",
            distinct_post_count=4,
            distinct_account_count=3,
            verification_passed=True,
        )


class Candidate:
    def __init__(self, slug: str, title: str) -> None:
        self.slug = slug
        self.title = title
        self.market_url = f"https://polymarket.com/event/{slug}"
        self.source_label = "breaking"


def test_cross_signal_orchestrator_emits_only_verified_topics():
    orchestrator = CrossSignalOrchestrator(
        scout=StubScout(
            [
                Candidate("kitkat-heist-response", "Will KitKat issue a statement about the heist by April 8?"),
                Candidate("openai-release-gpt6-this-week", "Will OpenAI release GPT-6 this week?"),
            ]
        ),
        gate=StubGate({"kitkat-heist-response"}),
    )

    report = orchestrator.run()

    assert report.candidate_count == 2
    assert report.passed_count == 1
    assert [item.topic for item in report.topics] == ["kitkat-heist-response"]
