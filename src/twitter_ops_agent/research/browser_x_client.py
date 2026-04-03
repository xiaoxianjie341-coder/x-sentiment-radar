from __future__ import annotations

import json
from typing import Callable
from urllib import parse

import httpx
from twscrape.api import GQL_FEATURES, GQL_URL, OP_TweetDetail
from twscrape.models import parse_tweet, parse_tweets

from twitter_ops_agent.discovery.attentionvc import AttentionTweet
from twitter_ops_agent.research.twscrape_client import _to_attention_tweet


class BrowserXSessionCrowdClient:
    def __init__(
        self,
        *,
        cookie_header: str,
        x_client_transaction_id: str,
        user_agent: str,
        request_get: Callable[[str, dict[str, str]], httpx.Response] | None = None,
        tweet_parser: Callable[[httpx.Response, int], object | None] | None = None,
        tweets_parser: Callable[[httpx.Response, int], list[object]] | None = None,
    ) -> None:
        self.cookie_header = cookie_header.strip()
        self.x_client_transaction_id = x_client_transaction_id.strip()
        self.user_agent = user_agent.strip()
        self.request_get = request_get or _default_request_get
        self.tweet_parser = tweet_parser or parse_tweet
        self.tweets_parser = tweets_parser or (lambda rep, limit: list(parse_tweets(rep, limit=limit)))

        if not self.cookie_header:
            raise RuntimeError("X browser session cookie header is required.")
        if not self.x_client_transaction_id:
            raise RuntimeError("X browser session x-client-transaction-id is required.")

        self.csrf_token = _extract_cookie_value(self.cookie_header, "ct0")
        if not self.csrf_token:
            raise RuntimeError("X browser session cookie header must include ct0.")

    def tweet_details(self, *, tweet_id: str) -> AttentionTweet | None:
        rep = self._tweet_detail_request(tweet_id=tweet_id)
        parsed = self.tweet_parser(rep, int(tweet_id))
        return _to_attention_tweet(parsed) if parsed is not None else None

    def tweet_thread(self, *, tweet_id: str) -> list[AttentionTweet]:
        detail = self.tweet_details(tweet_id=tweet_id)
        return [detail] if detail is not None else []

    def tweet_replies(self, *, tweet_id: str, limit: int = 20) -> list[AttentionTweet]:
        collected: list[AttentionTweet] = []
        seen_ids: set[str] = set()
        cursor: str | None = None
        target_id = int(tweet_id)

        while len(collected) < limit:
            rep = self._tweet_detail_request(tweet_id=tweet_id, cursor=cursor)
            for tweet in self.tweets_parser(rep, limit):
                if int(getattr(tweet, "id", 0) or 0) == target_id:
                    continue
                if int(getattr(tweet, "inReplyToTweetId", 0) or 0) != target_id:
                    continue
                mapped = _to_attention_tweet(tweet)
                if mapped.tweet_id in seen_ids:
                    continue
                seen_ids.add(mapped.tweet_id)
                collected.append(mapped)
                if len(collected) >= limit:
                    break
            if len(collected) >= limit:
                break
            cursor = _find_cursor(rep.json(), cursor_type="ShowMoreThreads")
            if not cursor:
                break

        return collected[:limit]

    def search_tweets(self, *, query: str, limit: int = 20) -> list[AttentionTweet]:  # noqa: ARG002
        return []

    def _tweet_detail_request(self, *, tweet_id: str, cursor: str | None = None) -> httpx.Response:
        variables = {
            "focalTweetId": str(tweet_id),
            "with_rux_injections": True,
            "includePromotedContent": True,
            "withCommunity": True,
            "withQuickPromoteEligibilityTweetFields": True,
            "withBirdwatchNotes": True,
            "withVoice": True,
            "withV2Timeline": True,
        }
        if cursor:
            variables["cursor"] = cursor
            variables["referrer"] = "tweet"
        params = {
            "variables": json.dumps(variables, separators=(",", ":")),
            "features": json.dumps(GQL_FEATURES, separators=(",", ":")),
        }
        url = f"{GQL_URL}/{OP_TweetDetail}?{parse.urlencode(params)}"
        rep = self.request_get(url, self._headers())
        rep.raise_for_status()
        return rep

    def _headers(self) -> dict[str, str]:
        return {
            "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
            "x-csrf-token": self.csrf_token,
            "x-twitter-client-language": "zh-cn",
            "x-twitter-active-user": "yes",
            "x-twitter-auth-type": "OAuth2Session",
            "x-client-transaction-id": self.x_client_transaction_id,
            "user-agent": self.user_agent,
            "content-type": "application/json",
            "cookie": self.cookie_header,
        }


def _default_request_get(url: str, headers: dict[str, str]) -> httpx.Response:
    return httpx.get(url, headers=headers, timeout=20)


def _extract_cookie_value(cookie_header: str, key: str) -> str:
    prefix = f"{key}="
    for item in cookie_header.split(";"):
        token = item.strip()
        if token.startswith(prefix):
            return token[len(prefix) :]
    return ""


def _find_cursor(payload: object, *, cursor_type: str) -> str | None:
    if isinstance(payload, dict):
        if payload.get("cursorType") == cursor_type and payload.get("value"):
            return str(payload["value"])
        for value in payload.values():
            found = _find_cursor(value, cursor_type=cursor_type)
            if found:
                return found
        return None
    if isinstance(payload, list):
        for item in payload:
            found = _find_cursor(item, cursor_type=cursor_type)
            if found:
                return found
    return None
