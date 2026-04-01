from __future__ import annotations

from twitter_ops_agent.domain.models import Candidate, CaptureResult, EventContext, EventLink, LinkedCapture


def link_capture_to_event(capture: CaptureResult, event_context: EventContext) -> EventLink:
    if capture.source_post and capture.source_post.post_id in event_context.by_post_id:
        return EventLink(
            event_id=event_context.by_post_id[capture.source_post.post_id],
            source_role="seed_news",
            target_role="target_take",
        )

    if (
        capture.target_post.conversation_id
        and capture.target_post.conversation_id in event_context.by_conversation_id
    ):
        return EventLink(
            event_id=event_context.by_conversation_id[capture.target_post.conversation_id],
            source_role="seed_news" if capture.source_post else "seed_news",
            target_role="target_take" if capture.source_post else "seed_news",
        )

    if capture.target_post.conversation_id:
        return EventLink(
            event_id=f"conv:{capture.target_post.conversation_id}",
            source_role="seed_news" if capture.source_post else "seed_news",
            target_role="target_take" if capture.source_post else "seed_news",
        )

    return EventLink(
        event_id=f"post:{capture.source_post.post_id if capture.source_post else capture.target_post.post_id}",
        source_role="seed_news" if capture.source_post else "seed_news",
        target_role="target_take" if capture.source_post else "seed_news",
    )


def persist_event_link(repo, capture: CaptureResult, event_link: EventLink) -> None:
    repo.persist_event_link(capture, event_link)


def link_many(captures: list[CaptureResult], event_context: EventContext) -> list[LinkedCapture]:
    linked: list[LinkedCapture] = []
    for capture in captures:
        event_link = link_capture_to_event(capture, event_context=event_context)
        linked.append(
            LinkedCapture(
                capture=capture,
                event_link=event_link,
                candidate=Candidate(
                    event_id=event_link.event_id,
                    track=capture.target_post.track,
                    source_tier="normal",
                    views=capture.target_post.views,
                    batch_view_median=float(capture.target_post.views or 0),
                    related_event=event_link.event_id in event_context.by_post_id.values()
                    or event_link.event_id in event_context.by_conversation_id.values(),
                    has_market_or_regulatory_signal=False,
                ),
            )
        )
    return linked


class EventService:
    def __init__(self, repo) -> None:
        self.repo = repo

    def link_many(self, captures: list[CaptureResult], event_context: EventContext) -> list[LinkedCapture]:
        return link_many(captures=captures, event_context=event_context)

    def persist_many(self, linked: list[LinkedCapture]) -> None:
        for item in linked:
            persist_event_link(self.repo, item.capture, item.event_link)
