from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from twitter_ops_agent.discovery.attentionvc import AttentionTweet


class TwscrapeCrowdClient:
    def __init__(self, *, api: object, search_enabled: bool = False) -> None:
        self.api = api
        self.search_enabled = search_enabled

    @classmethod
    def from_db(cls, db_file, *, search_enabled: bool = False, x_client_transaction_id: str = ""):
        try:
            from twscrape import API
        except ImportError as exc:  # pragma: no cover - exercised via CLI wiring
            raise RuntimeError("twscrape is not installed. Run `pip install twscrape`.") from exc
        if x_client_transaction_id:
            _install_static_x_client_transaction_id(x_client_transaction_id)
        return cls(api=API(str(db_file), raise_when_no_account=True), search_enabled=search_enabled)

    def tweet_details(self, *, tweet_id: str) -> AttentionTweet | None:
        try:
            detail = _run_async(self.api.tweet_details(int(tweet_id)))
        except Exception as exc:
            raise RuntimeError(f"twscrape request failed: {exc}") from exc
        if detail is None:
            return None
        return _to_attention_tweet(detail)

    def tweet_thread(self, *, tweet_id: str) -> list[AttentionTweet]:
        detail = self.tweet_details(tweet_id=tweet_id)
        return [detail] if detail is not None else []

    def tweet_replies(self, *, tweet_id: str, limit: int = 20) -> list[AttentionTweet]:
        try:
            items = _run_async(_collect(self.api.tweet_replies(int(tweet_id), limit=limit), limit=limit))
        except Exception as exc:
            raise RuntimeError(f"twscrape request failed: {exc}") from exc
        replies = []
        target_id = int(tweet_id)
        for item in items:
            if int(getattr(item, "inReplyToTweetId", 0) or 0) != target_id:
                continue
            replies.append(_to_attention_tweet(item))
        return replies[:limit]

    def search_tweets(self, *, query: str, limit: int = 20) -> list[AttentionTweet]:
        if not self.search_enabled or not hasattr(self.api, "search"):
            return []
        try:
            items = _run_async(_collect(self.api.search(query, limit=limit), limit=limit))
        except Exception as exc:
            raise RuntimeError(f"twscrape request failed: {exc}") from exc
        return [_to_attention_tweet(item) for item in items][:limit]


async def _collect(generator: Any, *, limit: int) -> list[object]:
    items: list[object] = []
    async for item in generator:
        items.append(item)
        if limit > 0 and len(items) >= limit:
            break
    return items


def _run_async(awaitable):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    raise RuntimeError("TwscrapeCrowdClient cannot run inside an active event loop.")


def _install_static_x_client_transaction_id(value: str) -> None:
    from twscrape.queue_client import XClIdGenStore

    class _StaticXClId:
        def __init__(self, raw: str) -> None:
            self.raw = raw

        def calc(self, method: str, path: str) -> str:  # noqa: ARG002
            return self.raw

    async def _get(username: str, fresh: bool = False):  # noqa: ARG001
        return _StaticXClId(value)

    XClIdGenStore.get = _get


def _to_attention_tweet(tweet: object) -> AttentionTweet:
    user = getattr(tweet, "user", None)
    published_at = getattr(tweet, "date", None) or datetime.now(timezone.utc)
    return AttentionTweet(
        tweet_id=str(getattr(tweet, "id")),
        text=str(getattr(tweet, "rawContent", "")).strip(),
        url=str(getattr(tweet, "url", "")).strip(),
        published_at=published_at,
        author_handle=str(getattr(user, "username", "")).strip(),
        author_name=str(getattr(user, "displayname", "")).strip(),
        author_followers=int(getattr(user, "followersCount", 0) or 0),
        author_is_blue_verified=bool(getattr(user, "verified", False)),
        views=int(getattr(tweet, "viewCount", 0) or 0),
        likes=int(getattr(tweet, "likeCount", 0) or 0),
        retweets=int(getattr(tweet, "retweetCount", 0) or 0),
        replies=int(getattr(tweet, "replyCount", 0) or 0),
        quotes=int(getattr(tweet, "quoteCount", 0) or 0),
        bookmarks=int(getattr(tweet, "bookmarkedCount", 0) or 0),
        lang=None,
        conversation_id=str(getattr(tweet, "id")),
    )
