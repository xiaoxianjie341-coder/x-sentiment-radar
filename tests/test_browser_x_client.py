from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import unquote

import httpx

from twitter_ops_agent.research.browser_x_client import BrowserXSessionCrowdClient


@dataclass
class StubUser:
    username: str
    displayname: str
    followersCount: int
    verified: bool = False


@dataclass
class StubTweet:
    id: int
    rawContent: str
    url: str
    date: datetime
    user: StubUser
    viewCount: int | None
    likeCount: int
    retweetCount: int
    replyCount: int
    quoteCount: int
    bookmarkedCount: int
    inReplyToTweetId: int | None = None


def _tweet(tweet_id: int, *, text: str, in_reply_to: int | None = None):
    return StubTweet(
        id=tweet_id,
        rawContent=text,
        url=f"https://x.com/example/status/{tweet_id}",
        date=datetime(2026, 4, 3, tzinfo=timezone.utc),
        user=StubUser(username=f"user_{tweet_id}", displayname=f"User {tweet_id}", followersCount=100 + tweet_id),
        viewCount=1000 + tweet_id,
        likeCount=50,
        retweetCount=5,
        replyCount=6,
        quoteCount=1,
        bookmarkedCount=2,
        inReplyToTweetId=in_reply_to,
    )


class StubRequester:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str]]] = []

    def __call__(self, url: str, headers: dict[str, str]) -> httpx.Response:
        self.calls.append((url, headers))
        page = "two" if "next-cursor" in unquote(url) else "one"
        payload = {
            "data": {
                "threaded_conversation_with_injections_v2": {
                    "instructions": [
                        {
                            "entries": [
                                {
                                    "content": {
                                        "cursorType": "ShowMoreThreads",
                                        "value": "next-cursor",
                                    }
                                }
                            ]
                        }
                    ]
                }
            },
            "page": page,
        }
        if page == "two":
            payload["data"]["threaded_conversation_with_injections_v2"]["instructions"][0]["entries"] = []
        request = httpx.Request("GET", url, headers=headers)
        return httpx.Response(200, json=payload, request=request)


def test_browser_x_client_uses_cookie_session_headers_for_tweet_details():
    requester = StubRequester()
    detail = _tweet(101, text="Source tweet")
    client = BrowserXSessionCrowdClient(
        cookie_header="auth_token=demo; ct0=csrf123",
        x_client_transaction_id="xctid",
        user_agent="TestAgent/1.0",
        request_get=requester,
        tweet_parser=lambda rep, twid: detail,
        tweets_parser=lambda rep, limit: [],
    )

    parsed = client.tweet_details(tweet_id="101")

    assert parsed is not None
    assert parsed.tweet_id == "101"
    assert requester.calls[0][1]["x-csrf-token"] == "csrf123"
    assert requester.calls[0][1]["x-client-transaction-id"] == "xctid"
    assert requester.calls[0][1]["cookie"] == "auth_token=demo; ct0=csrf123"


def test_browser_x_client_paginates_replies_and_filters_direct_children():
    requester = StubRequester()

    def tweets_parser(rep: httpx.Response, limit: int):
        page = rep.json()["page"]
        if page == "one":
            return [
                _tweet(201, text="Direct reply one", in_reply_to=101),
                _tweet(202, text="Nested reply", in_reply_to=201),
            ]
        return [_tweet(203, text="Direct reply two", in_reply_to=101)]

    client = BrowserXSessionCrowdClient(
        cookie_header="auth_token=demo; ct0=csrf123",
        x_client_transaction_id="xctid",
        user_agent="TestAgent/1.0",
        request_get=requester,
        tweet_parser=lambda rep, twid: _tweet(101, text="Source tweet"),
        tweets_parser=tweets_parser,
    )

    replies = client.tweet_replies(tweet_id="101", limit=5)

    assert [item.tweet_id for item in replies] == ["201", "203"]
    assert len(requester.calls) == 2
