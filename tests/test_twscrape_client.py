from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import sys
from types import SimpleNamespace

from twitter_ops_agent.research.twscrape_client import TwscrapeCrowdClient


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


class StubAPI:
    def __init__(self, detail_item: StubTweet, reply_items: list[StubTweet]) -> None:
        self.detail_item = detail_item
        self.reply_items = reply_items
        self.queries: list[tuple[str, int]] = []

    async def tweet_details(self, twid: int):
        self.queries.append(("details", twid))
        return self.detail_item if twid == self.detail_item.id else None

    def tweet_replies(self, twid: int, limit: int = -1):
        self.queries.append(("replies", twid))

        async def _gen():
            count = 0
            for item in self.reply_items:
                if limit > 0 and count >= limit:
                    break
                count += 1
                yield item

        return _gen()


def _tweet(tweet_id: int, *, text: str, in_reply_to: int | None = None, views: int | None = 0):
    return StubTweet(
        id=tweet_id,
        rawContent=text,
        url=f"https://x.com/example/status/{tweet_id}",
        date=datetime(2026, 4, 2, tzinfo=timezone.utc),
        user=StubUser(
            username=f"user_{tweet_id}",
            displayname=f"User {tweet_id}",
            followersCount=100 + tweet_id,
            verified=tweet_id % 2 == 0,
        ),
        viewCount=views,
        likeCount=40,
        retweetCount=5,
        replyCount=12,
        quoteCount=2,
        bookmarkedCount=3,
        inReplyToTweetId=in_reply_to,
    )


def test_twscrape_client_maps_tweet_details_and_builds_seed_thread():
    api = StubAPI(
        detail_item=_tweet(101, text="Anthropic shipped a new coding workflow.", views=9999),
        reply_items=[],
    )
    client = TwscrapeCrowdClient(api=api)

    detail = client.tweet_details(tweet_id="101")
    thread = client.tweet_thread(tweet_id="101")

    assert detail is not None
    assert detail.tweet_id == "101"
    assert detail.views == 9999
    assert detail.author_handle == "user_101"
    assert [item.tweet_id for item in thread] == ["101"]


def test_twscrape_client_only_returns_direct_replies():
    api = StubAPI(
        detail_item=_tweet(101, text="Anthropic shipped a new coding workflow.", views=9999),
        reply_items=[
            _tweet(201, text="Direct reply one with useful detail.", in_reply_to=101, views=1200),
            _tweet(202, text="Nested reply that should be ignored.", in_reply_to=201, views=800),
            _tweet(203, text="Direct reply two with more detail.", in_reply_to=101, views=1300),
        ],
    )
    client = TwscrapeCrowdClient(api=api)

    replies = client.tweet_replies(tweet_id="101", limit=10)

    assert [item.tweet_id for item in replies] == ["201", "203"]
    assert replies[0].likes == 40
    assert replies[0].quotes == 2


def test_twscrape_client_from_db_enables_fail_fast_account_selection(monkeypatch):
    calls: list[tuple[str, bool]] = []

    class StubAPIClass:
        def __init__(self, db_file: str, raise_when_no_account: bool = False):
            calls.append((db_file, raise_when_no_account))

    monkeypatch.setitem(sys.modules, "twscrape", SimpleNamespace(API=StubAPIClass))

    client = TwscrapeCrowdClient.from_db("data/twscrape/accounts.db", search_enabled=False)

    assert isinstance(client.api, StubAPIClass)
    assert calls == [("data/twscrape/accounts.db", True)]


def test_twscrape_client_from_db_can_install_static_x_client_transaction_id(monkeypatch):
    calls: list[tuple[str, bool]] = []

    class StubAPIClass:
        def __init__(self, db_file: str, raise_when_no_account: bool = False):
            calls.append((db_file, raise_when_no_account))

    dummy_store = SimpleNamespace(get=None)
    monkeypatch.setitem(sys.modules, "twscrape", SimpleNamespace(API=StubAPIClass))
    monkeypatch.setitem(sys.modules, "twscrape.queue_client", SimpleNamespace(XClIdGenStore=dummy_store))

    TwscrapeCrowdClient.from_db(
        "data/twscrape/accounts.db",
        search_enabled=False,
        x_client_transaction_id="static-xctid",
    )

    assert calls == [("data/twscrape/accounts.db", True)]
    assert dummy_store.get is not None


def test_twscrape_client_surfaces_clear_runtime_errors():
    class BrokenAPI:
        async def tweet_details(self, twid: int):
            raise RuntimeError("No account available for queue TweetDetail")

    client = TwscrapeCrowdClient(api=BrokenAPI())

    try:
        client.tweet_details(tweet_id="123")
    except RuntimeError as exc:
        assert str(exc) == "twscrape request failed: No account available for queue TweetDetail"
    else:  # pragma: no cover - defensive
        raise AssertionError("expected runtime error")
