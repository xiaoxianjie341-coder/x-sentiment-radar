from __future__ import annotations

import json

from twitter_ops_agent.discovery.polymarket import (
    PolymarketCandidate,
    PolymarketSignalScout,
    candidate_from_anomaly,
    parse_breaking_candidates,
)


def _breaking_html(*items: dict[str, object]) -> str:
    payload = {
        "props": {
            "pageProps": {
                "dehydratedState": {
                    "queries": [
                        {
                            "state": {
                                "data": {
                                    "data": list(items),
                                }
                            }
                        }
                    ]
                }
            }
        }
    }
    return (
        '<html><body><script id="__NEXT_DATA__" type="application/json">'
        f"{json.dumps(payload, ensure_ascii=False)}"
        "</script></body></html>"
    )


def test_parse_breaking_candidates_extracts_relevant_public_interest_topics():
    html = _breaking_html(
        {
            "id": "1",
            "title": "Will KitKat issue a statement about the heist by April 8?",
            "slug": "kitkat-heist-response",
            "volume24hr": 55000,
            "liquidity": 12000,
            "firstTag": "Culture",
            "firstTagSlug": "pop-culture",
            "secondTag": "Brand",
            "secondTagSlug": "brand",
            "markets": [{"id": "m1"}],
        },
        {
            "id": "2",
            "title": "What price will Chainlink hit in April?",
            "slug": "what-price-will-chainlink-hit-in-april",
            "volume24hr": 99000,
            "liquidity": 20000,
            "firstTag": "Crypto",
            "firstTagSlug": "crypto",
            "secondTag": "Crypto Prices",
            "secondTagSlug": "crypto-prices",
            "markets": [{"id": "m2"}],
        },
    )

    candidates = parse_breaking_candidates(html)

    assert [item.slug for item in candidates] == ["kitkat-heist-response"]
    assert candidates[0].title == "Will KitKat issue a statement about the heist by April 8?"
    assert candidates[0].market_url == "https://polymarket.com/event/kitkat-heist-response"
    assert candidates[0].category_slug == "pop-culture"
    assert candidates[0].source_label == "breaking"


def test_candidate_from_anomaly_normalizes_to_same_shape():
    candidate = candidate_from_anomaly(
        {
            "id": "anomaly-1",
            "title": "Will OpenAI ship a major GPT release this week?",
            "slug": "openai-major-gpt-release-this-week",
            "category": "tech",
            "volume24hr": 220000,
            "liquidity": 45000,
        }
    )

    assert candidate.market_id == "anomaly-1"
    assert candidate.slug == "openai-major-gpt-release-this-week"
    assert candidate.category_slug == "tech"
    assert candidate.source_label == "anomaly"


def test_polymarket_signal_scout_merges_breaking_and_anomaly_without_duplicates():
    html = _breaking_html(
        {
            "id": "1",
            "title": "Will OpenAI release GPT-6 this week?",
            "slug": "openai-release-gpt6-this-week",
            "volume24hr": 120000,
            "liquidity": 50000,
            "firstTag": "Tech",
            "firstTagSlug": "tech",
            "markets": [{"id": "m1"}],
        }
    )
    scout = PolymarketSignalScout(
        html_loader=lambda: html,
        filter_candidates=True,
        anomaly_loader=lambda: [
            {
                "id": "1b",
                "title": "Will OpenAI release GPT-6 this week?",
                "slug": "openai-release-gpt6-this-week",
                "category": "tech",
                "volume24hr": 140000,
                "liquidity": 51000,
            },
            {
                "id": "2",
                "title": "Will Michigan win the 2026 NCAA Tournament?",
                "slug": "michigan-win-the-2026-ncaa-tournament",
                "category": "sports",
                "volume24hr": 100000,
                "liquidity": 30000,
            },
        ],
    )

    candidates = scout.run()

    assert [item.slug for item in candidates] == ["openai-release-gpt6-this-week"]
    assert all(isinstance(item, PolymarketCandidate) for item in candidates)


def test_polymarket_signal_scout_respects_candidate_limit():
    html = _breaking_html(
        {
            "id": "1",
            "title": "Will OpenAI release GPT-6 this week?",
            "slug": "openai-release-gpt6-this-week",
            "volume24hr": 120000,
            "liquidity": 50000,
            "firstTag": "Tech",
            "firstTagSlug": "tech",
            "markets": [{"id": "m1"}],
        },
        {
            "id": "2",
            "title": "Will KitKat issue a statement about the heist by April 8?",
            "slug": "kitkat-heist-response",
            "volume24hr": 55000,
            "liquidity": 12000,
            "firstTag": "Culture",
            "firstTagSlug": "pop-culture",
            "markets": [{"id": "m2"}],
        },
    )
    scout = PolymarketSignalScout(
        html_loader=lambda: html,
        candidate_limit=1,
    )

    candidates = scout.run()

    assert [item.slug for item in candidates] == ["openai-release-gpt6-this-week"]


def test_polymarket_signal_scout_can_return_all_breaking_items_without_filtering():
    html = _breaking_html(
        {
            "id": "1",
            "title": "What price will Chainlink hit in April?",
            "slug": "what-price-will-chainlink-hit-in-april",
            "volume24hr": 99000,
            "liquidity": 20000,
            "firstTag": "Crypto",
            "firstTagSlug": "crypto",
            "secondTag": "Crypto Prices",
            "secondTagSlug": "crypto-prices",
            "markets": [{"id": "m1"}],
        },
        {
            "id": "2",
            "title": "NBA Atlantic Division Winner",
            "slug": "nba-2025-26-atlantic-division-winner",
            "volume24hr": 34000,
            "liquidity": 9000,
            "firstTag": "Sports",
            "firstTagSlug": "sports",
            "markets": [{"id": "m2"}],
        },
    )
    scout = PolymarketSignalScout(
        html_loader=lambda: html,
        candidate_limit=0,
        filter_candidates=False,
    )

    candidates = scout.run()

    assert [item.slug for item in candidates] == [
        "what-price-will-chainlink-hit-in-april",
        "nba-2025-26-atlantic-division-winner",
    ]
