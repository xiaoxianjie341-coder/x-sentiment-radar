from __future__ import annotations

import json

from twitter_ops_agent.discovery.polymarket import PolymarketCandidate
from twitter_ops_agent.v2.agents.grok_cross_signal_gate import GrokCrossSignalGate, XaiSearchConfig


def _candidate() -> PolymarketCandidate:
    return PolymarketCandidate(
        market_id="market-1",
        title="Will KitKat issue a statement about the heist by April 8, 2026?",
        slug="kitkat-heist-response",
        market_url="https://polymarket.com/event/kitkat-heist-response",
        category_label="Culture",
        category_slug="pop-culture",
        source_label="breaking",
    )


class StubResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_grok_cross_signal_gate_builds_xai_request_with_x_search_tool(monkeypatch):
    captured: dict[str, object] = {}

    def stub_urlopen(req, timeout):  # noqa: ANN001
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["timeout"] = timeout
        return StubResponse(
            {
                "output_text": json.dumps(
                    {
                        "is_viral": False,
                        "reason_if_not_viral": "noise",
                        "top_5_posts": [],
                        "one_line_angle": "",
                        "confidence": 12,
                    }
                )
            }
        )

    monkeypatch.setattr("twitter_ops_agent.v2.agents.grok_cross_signal_gate.request.urlopen", stub_urlopen)
    gate = GrokCrossSignalGate(
        config=XaiSearchConfig(
            api_key="secret",
            model="grok-4.20-reasoning",
        )
    )

    alert = gate.evaluate(_candidate())

    assert alert is None
    assert captured["url"] == "https://api.x.ai/v1/responses"
    assert captured["timeout"] == 30.0
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["body"]["model"] == "grok-4.20-reasoning"
    assert captured["body"]["tool_choice"] == "auto"
    assert {"type": "x_search"} in captured["body"]["tools"]


def test_grok_cross_signal_gate_maps_structured_output_to_alert(monkeypatch):
    def stub_urlopen(req, timeout):  # noqa: ANN001, ARG001
        return StubResponse(
            {
                "output_text": json.dumps(
                    {
                        "is_viral": True,
                        "reason_if_not_viral": "",
                        "top_5_posts": [
                            {
                                "text": "KitKat heist is turning into meme fuel.",
                                "url": "https://x.com/brandwatch/status/1",
                                "author_handle": "brandwatch",
                                "retweet_velocity": "high",
                                "secondary_engagement_desc": "quote tweets are compounding",
                            },
                            {
                                "text": "The KitKat story is escaping brand Twitter.",
                                "url": "https://x.com/adnews/status/2",
                                "author_handle": "adnews",
                                "retweet_velocity": "medium",
                                "secondary_engagement_desc": "marketing creators are riffing on it",
                            },
                        ],
                        "one_line_angle": "Brand mishap plus meme remix is the winning angle.",
                        "confidence": 88,
                    }
                )
            }
        )

    monkeypatch.setattr("twitter_ops_agent.v2.agents.grok_cross_signal_gate.request.urlopen", stub_urlopen)
    gate = GrokCrossSignalGate(
        config=XaiSearchConfig(
            api_key="secret",
            model="grok-4.20-reasoning",
        )
    )

    alert = gate.evaluate(_candidate(), queries=("kitkat heist", "kitkat meme"))

    assert alert is not None
    assert alert.verification_passed is True
    assert alert.topic == "kitkat heist"
    assert alert.distinct_post_count == 2
    assert alert.distinct_account_count == 2
    assert alert.angle_summary == "Brand mishap plus meme remix is the winning angle."
    assert [post.author_handle for post in alert.top_posts] == ["brandwatch", "adnews"]


def test_grok_cross_signal_gate_accepts_non_numeric_confidence(monkeypatch):
    def stub_urlopen(req, timeout):  # noqa: ANN001, ARG001
        return StubResponse(
            {
                "output_text": json.dumps(
                    {
                        "is_viral": True,
                        "reason_if_not_viral": "",
                        "top_5_posts": [],
                        "one_line_angle": "Angle",
                        "confidence": "high",
                    }
                )
            }
        )

    monkeypatch.setattr("twitter_ops_agent.v2.agents.grok_cross_signal_gate.request.urlopen", stub_urlopen)
    gate = GrokCrossSignalGate(
        config=XaiSearchConfig(
            api_key="secret",
            model="grok-4-1-fast-reasoning",
        )
    )

    alert = gate.evaluate(_candidate(), queries=("kitkat heist",))

    assert alert is not None
    assert alert.angle_summary == "Angle"
