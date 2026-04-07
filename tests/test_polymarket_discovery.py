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


def _zh_breaking_html() -> str:
    return """
    <html><body>
      <div class="flex flex-col transition-none pb-12">
        <a class="group cursor-pointer" href="/zh/event/march-2026-temperature-increase-c/will-global-temperature-increase-by-more-than-1pt29c-in-march-2026">
          <div class="flex flex-col gap-2 py-5 pl-0 pr-1 border-b group-last:border-b-0 relative">
            <div class="flex items-center justify-between cursor-pointer relative">
              <div class="flex-1 flex items-start gap-3">
                <div class="text-sm text-text-secondary font-medium min-w-[20px] mt-4">1</div>
                <div class="size-12 lg:size-13 shrink-0 relative">
                  <img alt="到2026年3月，全球气温将上升超过1.29ºC吗？" />
                </div>
                <div class="flex-1 min-w-0 flex-col flex">
                  <p class="text-[15px] font-medium mb-0.5 text-pretty line-clamp-3 group-hover:underline">到2026年3月，全球气温将上升超过1.29ºC吗？</p>
                  <div class="text-right flex items-center gap-1 hidden">
                    <span>11%</span>
                    <div class="flex items-center gap-0.5 mt-1.25 text-red-500"><span>47%</span></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </a>
        <a class="group cursor-pointer" href="/zh/event/claude-5-released-by/will-claude-5-be-released-by-may-31-2026">
          <div class="flex flex-col gap-2 py-5 pl-0 pr-1 border-b group-last:border-b-0 relative">
            <div class="flex items-center justify-between cursor-pointer relative">
              <div class="flex-1 flex items-start gap-3">
                <div class="text-sm text-text-secondary font-medium min-w-[20px] mt-4">2</div>
                <div class="size-12 lg:size-13 shrink-0 relative">
                  <img alt="Claude 5会在2026年5月31日之前发布吗？" />
                </div>
                <div class="flex-1 min-w-0 flex-col flex">
                  <p class="text-[15px] font-medium mb-0.5 text-pretty line-clamp-3 group-hover:underline">Claude 5会在2026年5月31日之前发布吗？</p>
                  <div class="text-right flex items-center gap-1 hidden">
                    <span>68%</span>
                    <div class="flex items-center gap-0.5 mt-1.25 text-green-600"><span>39%</span></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </a>
        <a class="group cursor-pointer" href="/zh/event/of-views-of-taylor-swifts-elizabeth-taylor-video-on-week-1/will-elizabeth-taylor-get-3-million-or-more-views-in-the-first-week">
          <div class="flex flex-col gap-2 py-5 pl-0 pr-1 border-b group-last:border-b-0 relative">
            <div class="flex items-center justify-between cursor-pointer relative">
              <div class="flex-1 flex items-start gap-3">
                <div class="text-sm text-text-secondary font-medium min-w-[20px] mt-4">3</div>
                <div class="size-12 lg:size-13 shrink-0 relative">
                  <img alt="Will &quot;Elizabeth Taylor&quot; get 3 million or more views in the first week?" />
                </div>
                <div class="flex-1 min-w-0 flex-col flex">
                  <p class="text-[15px] font-medium mb-0.5 text-pretty line-clamp-3 group-hover:underline">Will &quot;Elizabeth Taylor&quot; get 3 million or more views in the first week?</p>
                  <div class="text-right flex items-center gap-1 hidden">
                    <span>16%</span>
                    <div class="flex items-center gap-0.5 mt-1.25 text-red-500"><span>39%</span></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </a>
      </div>
    </body></html>
    """


def _zh_breaking_next_data_html() -> str:
    payload = {
        "props": {
            "pageProps": {
                "dehydratedState": {
                    "queries": [
                        {
                            "queryHash": '["biggest-movers","all"]',
                            "state": {
                                "data": {
                                    "markets": [
                                        {
                                            "id": "a1",
                                            "slug": "will-global-temperature-increase-by-more-than-1pt29c-in-march-2026",
                                            "question": "到2026年3月，全球气温将上升超过1.29ºC吗？",
                                            "currentPrice": 0.11,
                                            "livePriceChange": -47,
                                            "events": [{"slug": "march-2026-temperature-increase-c"}],
                                        },
                                        {
                                            "id": "a2",
                                            "slug": "will-claude-5-be-released-by-may-31-2026",
                                            "question": "Claude 5会在2026年5月31日之前发布吗？",
                                            "currentPrice": 0.68,
                                            "livePriceChange": 39,
                                            "events": [{"slug": "claude-5-released-by"}],
                                        },
                                    ]
                                }
                            },
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


def test_parse_breaking_candidates_can_extract_cards_from_zh_breaking_page():
    candidates = parse_breaking_candidates(_zh_breaking_html(), filter_candidates=False)

    assert [item.title for item in candidates] == [
        "到2026年3月，全球气温将上升超过1.29ºC吗？",
        "Claude 5会在2026年5月31日之前发布吗？",
        'Will "Elizabeth Taylor" get 3 million or more views in the first week?',
    ]
    assert candidates[0].market_url.endswith("/zh/event/march-2026-temperature-increase-c/will-global-temperature-increase-by-more-than-1pt29c-in-march-2026")
    assert candidates[1].current_probability == 68.0
    assert candidates[1].probability_change_24h == 39.0
    assert candidates[1].change_direction == "up"


def test_parse_breaking_candidates_prefers_zh_breaking_biggest_movers_query():
    candidates = parse_breaking_candidates(_zh_breaking_next_data_html(), filter_candidates=False)

    assert [item.title for item in candidates] == [
        "到2026年3月，全球气温将上升超过1.29ºC吗？",
        "Claude 5会在2026年5月31日之前发布吗？",
    ]
    assert candidates[0].market_url.endswith("/zh/event/march-2026-temperature-increase-c/will-global-temperature-increase-by-more-than-1pt29c-in-march-2026")
    assert candidates[0].current_probability == 11.0
    assert candidates[0].probability_change_24h == 47.0
    assert candidates[0].change_direction == "down"


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
