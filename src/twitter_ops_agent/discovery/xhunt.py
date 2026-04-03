from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Callable
from urllib import error, parse, request

from twitter_ops_agent.filter.track import classify_track
from twitter_ops_agent.v2.contracts import ScoutRunResult, ScoutSeed


_URL_RE = re.compile(r'https://twitter\.com/(?P<handle>[^/"]+)/status/(?P<tweet_id>\d+)')
_CONTENT_RE = re.compile(r'\\"content\\":\\"((?:\\\\.|[^"])*)\\"')
_HTML_TEXT_RE = re.compile(r'cursor-help">([^<]+)</p>', re.S)
_METRIC_RE = {
    "views": (
        re.compile(r'\\"title\\":\\"Views\\".{0,180}?\\"children\\":\\"([^"]+)\\"'),
        re.compile(r'title="Views".{0,500}?tabular-nums">([^<]+)<', re.S),
    ),
    "likes": (
        re.compile(r'\\"title\\":\\"Likes\\".{0,180}?\\"children\\":\\"([^"]+)\\"'),
        re.compile(r'title="Likes".{0,500}?tabular-nums">([^<]+)<', re.S),
    ),
    "retweets": (
        re.compile(r'\\"title\\":\\"Retweets\\".{0,180}?\\"children\\":\\"([^"]+)\\"'),
        re.compile(r'title="Retweets".{0,500}?tabular-nums">([^<]+)<', re.S),
    ),
}
_HEAT_RE = (
    re.compile(r'\\"value\\":([0-9]+(?:\.[0-9]+)?)'),
    re.compile(r'className":"text-xs","children":"([0-9]+(?:\.[0-9]+)?)"'),
    re.compile(r'text-xs">([0-9]+(?:\.[0-9]+)?)<'),
)


@dataclass(slots=True)
class XHuntHotTweet:
    tweet_id: str
    url: str
    author_handle: str
    text: str
    views: int
    likes: int
    retweets: int
    heat: float
    rank: int


class XHuntTrendClient:
    def __init__(
        self,
        *,
        base_url: str = "https://trends.xhunt.ai",
        timeout: float = 20.0,
        html_loader: Callable[..., str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.html_loader = html_loader

    def hot_tweets(self, *, group: str = "global", hours: int = 4, limit: int = 200) -> list[XHuntHotTweet]:
        html = self.html_loader(group=group, hours=hours) if self.html_loader is not None else self._fetch_html(group=group, hours=hours)
        return parse_hot_tweets(html)[:limit]

    def _fetch_html(self, *, group: str, hours: int) -> str:
        url = f"{self.base_url}/en/tweets?{parse.urlencode({'group': group, 'hours': hours})}"
        req = request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            method="GET",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                return response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"XHunt request failed with HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"XHunt request failed: {exc.reason}") from exc


class XHuntScoutAgent:
    def __init__(
        self,
        *,
        client: XHuntTrendClient,
        group: str | None = None,
        groups: tuple[str, ...] | None = None,
        hours: int = 24,
        limit: int = 15,
        min_views: int = 1000,
        min_likes: int = 10,
        state_size: int = 200,
    ) -> None:
        self.client = client
        self.groups = _resolve_groups(groups=groups, group=group)
        self.group = self.groups[0]
        self.hours = hours
        self.limit = limit
        self.min_views = min_views
        self.min_likes = min_likes
        self.state_size = state_size

    def fetch_since(self, last_seen: str | None) -> ScoutRunResult:
        previous_seen = _parse_seen_state(last_seen)
        seen_ids = set(previous_seen)
        scoped_items: list[tuple[str, XHuntHotTweet]] = []
        for group in self.groups:
            scoped_items.extend(
                (group, item)
                for item in self.client.hot_tweets(group=group, hours=self.hours, limit=self.limit)
            )
        unique_items = _dedupe_scoped_items(scoped_items)
        seeds = [
            _seed_from_hot_tweet(item, query=group)
            for group, item in unique_items
            if _passes_thresholds(item, self)
        ]
        fresh = [seed for seed in seeds if seed.tweet_id not in seen_ids]
        next_seen_state = json.dumps(
            _merge_seen_ids([item.tweet_id for _, item in unique_items], previous_seen, self.state_size),
            ensure_ascii=False,
        )
        return ScoutRunResult(seeds=fresh, next_seen_state=next_seen_state)

    def run(self) -> list[ScoutSeed]:
        return self.fetch_since(last_seen=None).seeds


def parse_hot_tweets(html: str) -> list[XHuntHotTweet]:
    matches = list(_URL_RE.finditer(html))
    items: list[XHuntHotTweet] = []
    seen: set[str] = set()

    for index, match in enumerate(matches, start=1):
        tweet_id = match.group("tweet_id")
        if tweet_id in seen:
            continue
        seen.add(tweet_id)

        start = match.start()
        end = matches[index].start() if index < len(matches) else len(html)
        block = html[start:end]
        text = _extract_content(block)
        items.append(
            XHuntHotTweet(
                tweet_id=tweet_id,
                url=match.group(0),
                author_handle=match.group("handle"),
                text=text,
                views=_extract_metric(block, "views"),
                likes=_extract_metric(block, "likes"),
                retweets=_extract_metric(block, "retweets"),
                heat=_extract_heat(block),
                rank=index,
            )
        )

    return items


def _extract_content(block: str) -> str:
    match = _CONTENT_RE.search(block)
    if match:
        return _decode_json_string(match.group(1)).strip()
    match = _HTML_TEXT_RE.search(block)
    if match:
        return _html_unescape(match.group(1)).strip()
    return ""


def _extract_metric(block: str, name: str) -> int:
    for pattern in _METRIC_RE[name]:
        match = pattern.search(block)
        if not match:
            continue
        value = match.group(1)
        if '\\"' in pattern.pattern:
            return _parse_compact_int(_decode_json_string(value))
        return _parse_compact_int(_html_unescape(value))
    return 0


def _extract_heat(block: str) -> float:
    for pattern in _HEAT_RE:
        match = pattern.search(block)
        if match:
            return float(match.group(1))
    return 0.0


def _decode_json_string(value: str) -> str:
    return json.loads(f'"{value}"')


def _html_unescape(value: str) -> str:
    return (
        value.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
    )


def _parse_compact_int(value: str) -> int:
    cleaned = value.strip().replace(",", "").upper()
    if not cleaned:
        return 0
    multiplier = 1
    if cleaned.endswith("K"):
        cleaned = cleaned[:-1]
        multiplier = 1_000
    elif cleaned.endswith("M"):
        cleaned = cleaned[:-1]
        multiplier = 1_000_000
    elif cleaned.endswith("B"):
        cleaned = cleaned[:-1]
        multiplier = 1_000_000_000
    return int(float(cleaned) * multiplier)


def _seed_from_hot_tweet(item: XHuntHotTweet, *, query: str) -> ScoutSeed:
    text = item.text.strip()
    title = " ".join(text.split())[:120] or item.tweet_id
    return ScoutSeed(
        seed_id=f"xhunt:{item.tweet_id}",
        source_kind="tweet",
        query=query,
        tweet_id=item.tweet_id,
        url=item.url,
        text=text,
        title=title,
        track=classify_track(text, item.author_handle),
        author_handle=item.author_handle,
        views=item.views,
        replies=0,
        likes=item.likes,
        velocity_hint=item.heat,
    )


def _passes_thresholds(item: XHuntHotTweet, agent: XHuntScoutAgent) -> bool:
    return item.views >= agent.min_views and item.likes >= agent.min_likes


def _dedupe_by_tweet_id(items: list[XHuntHotTweet]) -> list[XHuntHotTweet]:
    seen: set[str] = set()
    deduped: list[XHuntHotTweet] = []
    for item in items:
        if item.tweet_id in seen:
            continue
        seen.add(item.tweet_id)
        deduped.append(item)
    return deduped


def _dedupe_scoped_items(items: list[tuple[str, XHuntHotTweet]]) -> list[tuple[str, XHuntHotTweet]]:
    seen: set[str] = set()
    deduped: list[tuple[str, XHuntHotTweet]] = []
    for group, item in items:
        if item.tweet_id in seen:
            continue
        seen.add(item.tweet_id)
        deduped.append((group, item))
    return deduped


def _resolve_groups(*, groups: tuple[str, ...] | None, group: str | None) -> tuple[str, ...]:
    if groups:
        cleaned = tuple(item.strip() for item in groups if item and item.strip())
        if cleaned:
            return cleaned
    if group and group.strip():
        return (group.strip(),)
    return ("cn", "global")


def _parse_seen_state(last_seen: str | None) -> list[str]:
    if not last_seen:
        return []
    try:
        payload = json.loads(last_seen)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [str(item) for item in payload if str(item).strip()]


def _merge_seen_ids(current_ids: list[str], previous_seen: list[str], state_size: int) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for tweet_id in [*current_ids, *previous_seen]:
        if tweet_id in seen:
            continue
        seen.add(tweet_id)
        merged.append(tweet_id)
        if len(merged) >= state_size:
            break
    return merged
