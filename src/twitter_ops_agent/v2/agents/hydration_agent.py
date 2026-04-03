from __future__ import annotations

from dataclasses import dataclass

from twitter_ops_agent.domain.models import Account, CaptureResult, Post, utc_now
from twitter_ops_agent.events.linker import EventService
from twitter_ops_agent.filter.track import classify_track
from twitter_ops_agent.storage.repository import SqliteRepository
from twitter_ops_agent.v2.contracts import HydratedSeed, ScoutSeed


@dataclass(slots=True)
class HydrationAgent:
    repo: SqliteRepository
    events: EventService
    source_fetcher: object | None = None

    def run(self, seeds: list[ScoutSeed]) -> list[HydratedSeed]:
        if not seeds:
            return []
        hydrated_seeds = [self._hydrate_seed(seed) for seed in seeds]
        captures = [self._capture_from_seed(seed) for seed in hydrated_seeds]
        for capture in captures:
            self.repo.save_capture_result(capture)
        event_context = self.repo.load_event_context(
            post_ids=[capture.target_post.post_id for capture in captures],
            conversation_ids=[capture.target_post.conversation_id for capture in captures],
        )
        linked = self.events.link_many(captures, event_context=event_context)
        self.events.persist_many(linked)
        return [
            HydratedSeed(
                seed=seed,
                event_id=item.event_link.event_id,
                source_url=item.capture.target_post.url,
                source_text=item.capture.target_post.text_exact,
                track=item.capture.target_post.track,
            )
            for seed, item in zip(hydrated_seeds, linked, strict=True)
        ]

    def _hydrate_seed(self, seed: ScoutSeed) -> ScoutSeed:
        if self.source_fetcher is None or not hasattr(self.source_fetcher, "tweet_details"):
            return seed
        detail = self.source_fetcher.tweet_details(tweet_id=seed.tweet_id)
        if detail is None:
            return seed
        text = detail.text.strip() or seed.text
        track = seed.track or classify_track(text, detail.author_handle)
        return ScoutSeed(
            seed_id=seed.seed_id,
            source_kind=seed.source_kind,
            query=seed.query,
            tweet_id=seed.tweet_id,
            url=detail.url or seed.url,
            text=text,
            title=" ".join(text.split())[:120] or seed.title,
            track=track,
            author_handle=detail.author_handle or seed.author_handle,
            views=detail.views,
            replies=detail.replies,
            likes=detail.likes,
            velocity_hint=seed.velocity_hint,
        )

    def _capture_from_seed(self, seed: ScoutSeed) -> CaptureResult:
        account = Account(
            account_id=f"v2:{seed.author_handle}",
            platform="x",
            handle=seed.author_handle,
            display_name=seed.author_handle,
        )
        post = Post(
            post_id=seed.tweet_id,
            account_id=account.account_id,
            url=seed.url,
            created_at=utc_now(),
            captured_at=utc_now(),
            text_exact=seed.text,
            text_normalized=seed.text.strip(),
            post_type="original",
            track=seed.track,
            conversation_id=seed.tweet_id,
            likes=seed.likes,
            replies=seed.replies,
            views=seed.views,
        )
        return CaptureResult(target_account=account, target_post=post)
