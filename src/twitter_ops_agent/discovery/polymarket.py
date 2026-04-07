from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Callable, Iterable, Mapping
from urllib import error, request


BREAKING_URL = "https://polymarket.com/predictions/breaking-news"
BASE_URL = "https://polymarket.com"

_NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(?P<payload>.*?)</script>', re.S)
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


class PolymarketSignalScout:
    def __init__(
        self,
        *,
        breaking_url: str = BREAKING_URL,
        html_loader: Callable[[], str] | None = None,
        anomaly_loader: Callable[[], Iterable[Mapping[str, object]]] | None = None,
    ) -> None:
        self.breaking_url = breaking_url
        self.html_loader = html_loader
        self.anomaly_loader = anomaly_loader

    def run(self) -> list[PolymarketCandidate]:
        html = self.html_loader() if self.html_loader is not None else _fetch_html(self.breaking_url)
        candidates = parse_breaking_candidates(html)
        if self.anomaly_loader is not None:
            candidates.extend(candidate_from_anomaly(item) for item in self.anomaly_loader())
        return _dedupe_candidates(candidate for candidate in candidates if is_relevant_candidate(candidate))


def parse_breaking_candidates(html: str) -> list[PolymarketCandidate]:
    payload = _extract_next_data(html)
    matches = _find_candidate_dicts(payload)
    candidates = [_candidate_from_mapping(item, source_label="breaking") for item in matches]
    return [candidate for candidate in _dedupe_candidates(candidates) if is_relevant_candidate(candidate)]


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
    )


def _extract_next_data(html: str) -> object:
    match = _NEXT_DATA_RE.search(html)
    if not match:
        return {}
    return json.loads(match.group("payload"))


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
