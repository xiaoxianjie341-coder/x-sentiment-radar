from __future__ import annotations

from dataclasses import dataclass

from twitter_ops_agent.domain.models import CrossSignalAlert, CrossSignalPost, CrossSignalReview
from twitter_ops_agent.v2.cross_signal import CrossSignalOrchestrator


@dataclass
class StubScout:
    items: list[object]

    def run(self):
        return list(self.items)


@dataclass
class StubGate:
    passed_for: set[str]
    calls: list[str] | None = None

    def review(self, candidate):
        if self.calls is not None:
            self.calls.append(candidate.slug)
        is_viral = candidate.slug in self.passed_for
        return CrossSignalReview(
            slug=candidate.slug,
            market_title=candidate.title,
            market_url=candidate.market_url,
            source_label=candidate.source_label,
            queries=("kitkat heist",),
            is_viral=is_viral,
            reason_if_not_viral="" if is_viral else "not enough spread",
            angle_summary="X 上当前跑出来的角度更偏：KitKat heist is taking over X." if is_viral else "Still too early.",
            confidence=80 if is_viral else 30,
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
            distinct_post_count=1,
            distinct_account_count=1,
        )

    def evaluate(self, candidate):
        review = self.review(candidate)
        if not review.is_viral:
            return None
        return CrossSignalAlert(
            topic=candidate.slug,
            market_title=review.market_title,
            market_url=review.market_url,
            source_label=review.source_label,
            queries=review.queries,
            top_posts=review.top_posts,
            angle_summary=review.angle_summary,
            distinct_post_count=review.distinct_post_count,
            distinct_account_count=review.distinct_account_count,
            verification_passed=True,
        )


class Candidate:
    def __init__(self, slug: str, title: str) -> None:
        self.slug = slug
        self.title = title
        self.market_url = f"https://polymarket.com/event/{slug}"
        self.source_label = "breaking"


@dataclass
class StubStateStore:
    seen: tuple[str, ...] = ()
    saved: tuple[str, ...] = ()

    def load_seen(self) -> tuple[str, ...]:
        return self.seen

    def save_seen(self, seen: tuple[str, ...]) -> None:
        self.saved = seen


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
    assert report.new_candidate_count == 2
    assert report.passed_count == 1
    assert len(report.reviewed_candidates) == 2
    assert [item.topic for item in report.topics] == ["kitkat-heist-response"]
    assert [item.slug for item in report.candidates] == ["kitkat-heist-response", "openai-release-gpt6-this-week"]
    assert [item.slug for item in report.new_candidates] == ["kitkat-heist-response", "openai-release-gpt6-this-week"]


def test_cross_signal_orchestrator_only_evaluates_new_candidates_and_updates_state():
    state_store = StubStateStore(seen=("kitkat-heist-response",))
    gate = StubGate({"openai-release-gpt6-this-week"}, calls=[])
    orchestrator = CrossSignalOrchestrator(
        scout=StubScout(
            [
                Candidate("kitkat-heist-response", "Will KitKat issue a statement about the heist by April 8?"),
                Candidate("openai-release-gpt6-this-week", "Will OpenAI release GPT-6 this week?"),
            ]
        ),
        gate=gate,
        state_store=state_store,
    )

    report = orchestrator.run()

    assert report.candidate_count == 2
    assert report.new_candidate_count == 1
    assert report.passed_count == 1
    assert len(report.reviewed_candidates) == 1
    assert gate.calls == ["openai-release-gpt6-this-week"]
    assert state_store.saved == ("kitkat-heist-response", "openai-release-gpt6-this-week")
    assert [item.slug for item in report.candidates] == ["kitkat-heist-response", "openai-release-gpt6-this-week"]
    assert [item.slug for item in report.new_candidates] == ["openai-release-gpt6-this-week"]


def test_cross_signal_orchestrator_can_force_review_all_candidates():
    state_store = StubStateStore(seen=("kitkat-heist-response",))
    gate = StubGate({"kitkat-heist-response", "openai-release-gpt6-this-week"}, calls=[])
    orchestrator = CrossSignalOrchestrator(
        scout=StubScout(
            [
                Candidate("kitkat-heist-response", "Will KitKat issue a statement about the heist by April 8?"),
                Candidate("openai-release-gpt6-this-week", "Will OpenAI release GPT-6 this week?"),
            ]
        ),
        gate=gate,
        state_store=state_store,
    )

    report = orchestrator.run(review_all=True)

    assert report.new_candidate_count == 2
    assert len(report.reviewed_candidates) == 2
    assert gate.calls == ["kitkat-heist-response", "openai-release-gpt6-this-week"]
