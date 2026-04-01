from __future__ import annotations

from dataclasses import dataclass

from twitter_ops_agent.domain.models import Account, CaptureResult, Post, utc_now
from twitter_ops_agent.events.linker import EventService
from twitter_ops_agent.storage.repository import SqliteRepository
from twitter_ops_agent.v2.contracts import HydratedSeed, ScoutSeed


@dataclass(slots=True)
class HydrationAgent:
    repo: SqliteRepository
    events: EventService

    def run(self, seeds: list[ScoutSeed]) -> list[HydratedSeed]:
        if not seeds:
            return []
        captures = [self._capture_from_seed(seed) for seed in seeds]
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
            for seed, item in zip(seeds, linked, strict=True)
        ]

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
