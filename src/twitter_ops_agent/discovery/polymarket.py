from __future__ import annotations

from dataclasses import dataclass
import html as html_lib
import json
import re
from typing import Any, Callable, Iterable, Mapping
from urllib import error, request


BREAKING_URL = "https://polymarket.com/zh/breaking"
BASE_URL = "https://polymarket.com"

_ZH_BREAKING_CARD_RE = re.compile(
    r'<a class="group cursor-pointer" href="(?P<href>/zh/event/[^"]+)".*?'
    r'group-hover:underline">(?P<title>.*?)</p>.*?'
    r'<span>(?P<prob>\d+)%</span>.*?'
    r'text-(?P<dir>red|green)[^"]*"><span>(?P<delta>\d+)%</span>',
    re.S,
)
_EXCLUDED_CATEGORY_SLUGS = {
    "sports",
    "esports",
    "crypto-prices",
    "airdrops",
}
_EXCLUDED_TITLE_PATTERNS = (
    re.compile(r"\bwhat price will\b", re.I),
    re.compile(r"\bairdrop\b", re.I),
)


@dataclass(slots=True)
class PolymarketCandidate:
    market_id: str
    title: str
    slug: str
    market_url: str
    category_label: str
    category_slug: str
    secondary_category_label: str = ""
    secondary_category_slug: str = ""
    volume_24h: float = 0.0
    liquidity: float = 0.0
    source_label: str = "breaking"
    current_probability: float = 0.0
    probability_change_24h: float = 0.0
    change_direction: str = ""


class PolymarketSignalScout:
    def __init__(
        self,
        *,
        breaking_url: str = BREAKING_URL,
        candidate_limit: int = 0,
        filter_candidates: bool = False,
        html_loader: Callable[[], str] | None = None,
        anomaly_loader: Callable[[], Iterable[Mapping[str, object]]] | None = None,
    ) -> None:
        self.breaking_url = breaking_url
        self.candidate_limit = candidate_limit
        self.filter_candidates = filter_candidates
        self.html_loader = html_loader
        self.anomaly_loader = anomaly_loader

    def run(self) -> list[PolymarketCandidate]:
        html = self.html_loader() if self.html_loader is not None else _fetch_html(self.breaking_url)
        candidates = parse_breaking_candidates(html, filter_candidates=self.filter_candidates)
        if self.anomaly_loader is not None:
            candidates.extend(candidate_from_anomaly(item) for item in self.anomaly_loader())
        deduped = _dedupe_candidates(
            candidate for candidate in candidates if (is_relevant_candidate(candidate) if self.filter_candidates else True)
        )
        if self.candidate_limit > 0:
            return deduped[: self.candidate_limit]
        return deduped


def parse_breaking_candidates(html: str, *, filter_candidates: bool = True) -> list[PolymarketCandidate]:
    payload = _extract_next_data(html)
    biggest_movers = _extract_zh_breaking_biggest_movers(payload)
    if biggest_movers:
        candidates = biggest_movers
    elif "/zh/event/" in html:
        candidates = _parse_zh_breaking_cards(html)
    else:
        matches = _find_candidate_dicts(payload)
        candidates = [_candidate_from_mapping(item, source_label="breaking") for item in matches]
    deduped = _dedupe_candidates(candidates)
    if filter_candidates:
        return [candidate for candidate in deduped if is_relevant_candidate(candidate)]
    return deduped


def candidate_from_anomaly(item: Mapping[str, object]) -> PolymarketCandidate:
    return _candidate_from_mapping(item, source_label="anomaly")


def is_relevant_candidate(candidate: PolymarketCandidate) -> bool:
    if candidate.category_slug in _EXCLUDED_CATEGORY_SLUGS:
        return False
    if candidate.secondary_category_slug in _EXCLUDED_CATEGORY_SLUGS:
        return False
    return not any(pattern.search(candidate.title) for pattern in _EXCLUDED_TITLE_PATTERNS)


def _candidate_from_mapping(item: Mapping[str, object], *, source_label: str) -> PolymarketCandidate:
    slug = str(item.get("slug", "")).strip()
    return PolymarketCandidate(
        market_id=str(item.get("id", slug)).strip(),
        title=str(item.get("title", "")).strip(),
        slug=slug,
        market_url=f"{BASE_URL}/event/{slug}",
        category_label=str(item.get("firstTag", item.get("category", ""))).strip(),
        category_slug=str(item.get("firstTagSlug", item.get("category_slug", item.get("category", "")))).strip().lower(),
        secondary_category_label=str(item.get("secondTag", "")).strip(),
        secondary_category_slug=str(item.get("secondTagSlug", "")).strip().lower(),
        volume_24h=float(item.get("volume24hr", item.get("volume_24h", item.get("volume", 0))) or 0),
        liquidity=float(item.get("liquidity", 0) or 0),
        source_label=source_label,
        current_probability=float(item.get("current_probability", 0) or 0),
        probability_change_24h=float(item.get("probability_change_24h", 0) or 0),
        change_direction=str(item.get("change_direction", "")).strip(),
    )


def _parse_zh_breaking_cards(html: str) -> list[PolymarketCandidate]:
    candidates: list[PolymarketCandidate] = []
    for index, match in enumerate(_ZH_BREAKING_CARD_RE.finditer(html), start=1):
        href = html_lib.unescape(match.group("href"))
        slug = href.strip("/").split("/event/", 1)[-1]
        title = html_lib.unescape(match.group("title")).strip()
        prob = float(match.group("prob"))
        delta = float(match.group("delta"))
        direction = "down" if match.group("dir") == "red" else "up"
        candidates.append(
            PolymarketCandidate(
                market_id=f"zh-breaking:{index}",
                title=title,
                slug=slug,
                market_url=f"{BASE_URL}{href}",
                category_label="全部",
                category_slug="all",
                source_label="breaking",
                current_probability=prob,
                probability_change_24h=delta,
                change_direction=direction,
            )
        )
    return candidates


def _extract_zh_breaking_biggest_movers(payload: object) -> list[PolymarketCandidate]:
    if not isinstance(payload, dict):
        return []
    queries = (
        payload.get("props", {})
        .get("pageProps", {})
        .get("dehydratedState", {})
        .get("queries", [])
    )
    if not isinstance(queries, list):
        return []
    for entry in queries:
        if not isinstance(entry, dict):
            continue
        query_hash = str(entry.get("queryHash", ""))
        query_key = entry.get("queryKey", [])
        if '["biggest-movers","all"]' != query_hash and not (
            isinstance(query_key, list) and len(query_key) >= 2 and query_key[0] == "biggest-movers" and query_key[1] == "all"
        ):
            continue
        data = entry.get("state", {}).get("data", {})
        if not isinstance(data, dict):
            continue
        markets = data.get("markets", [])
        if not isinstance(markets, list):
            continue
        candidates: list[PolymarketCandidate] = []
        for index, item in enumerate(markets, start=1):
            if not isinstance(item, dict):
                continue
            slug = str(item.get("slug", "")).strip()
            if not slug:
                continue
            change = float(item.get("livePriceChange", 0) or 0)
            events = item.get("events", [])
            event_slug = ""
            if isinstance(events, list) and events and isinstance(events[0], dict):
                event_slug = str(events[0].get("slug", "")).strip()
            event_prefix = f"/zh/event/{event_slug}/" if event_slug else "/zh/event/"
            candidates.append(
                PolymarketCandidate(
                    market_id=str(item.get("id", slug)).strip(),
                    title=str(item.get("question", item.get("title", ""))).strip(),
                    slug=slug,
                    market_url=f"{BASE_URL}{event_prefix}{slug}",
                    category_label="全部",
                    category_slug="all",
                    source_label="breaking",
                    current_probability=float(item.get("currentPrice", 0) or 0) * 100,
                    probability_change_24h=abs(change),
                    change_direction="down" if change < 0 else "up",
                )
            )
        return candidates
    return []


def _extract_next_data(html: str) -> object:
    marker = '<script id="__NEXT_DATA__"'
    start = html.find(marker)
    if start == -1:
        return {}
    start = html.find(">", start)
    if start == -1:
        return {}
    start += 1
    end = html.find("</script>", start)
    if end == -1:
        return {}
    return json.loads(html[start:end])


def _find_candidate_dicts(payload: object) -> list[Mapping[str, object]]:
    found: list[Mapping[str, object]] = []

    def visit(node: object) -> None:
        if isinstance(node, dict):
            if _looks_like_candidate(node):
                found.append(node)
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(payload)
    return found


def _looks_like_candidate(item: Mapping[str, object]) -> bool:
    return bool(item.get("title")) and bool(item.get("slug")) and ("markets" in item or "liquidity" in item)


def _dedupe_candidates(items: Iterable[PolymarketCandidate]) -> list[PolymarketCandidate]:
    seen: set[str] = set()
    ordered: list[PolymarketCandidate] = []
    for item in items:
        key = item.slug or item.market_id
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(item)
    return ordered


def _fetch_html(url: str) -> str:
    req = request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=20.0) as response:
            return response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Polymarket request failed with HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Polymarket request failed: {exc.reason}") from exc
