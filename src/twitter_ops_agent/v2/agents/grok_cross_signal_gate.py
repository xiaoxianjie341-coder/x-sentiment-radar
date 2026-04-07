from __future__ import annotations

from dataclasses import dataclass
import json
from urllib import error, request

from twitter_ops_agent.discovery.polymarket import PolymarketCandidate
from twitter_ops_agent.domain.models import CrossSignalAlert, CrossSignalPost, CrossSignalReview
from twitter_ops_agent.v2.agents.cross_signal_gate import build_topic_queries
from twitter_ops_agent.writer.llm_writer import build_endpoint, extract_text_from_response


@dataclass(slots=True)
class XaiSearchConfig:
    api_key: str
    model: str
    base_url: str = "https://api.x.ai/v1"
    reasoning_effort: str = ""
    timeout_seconds: float = 30.0
    max_retries: int = 1


@dataclass(slots=True)
class GrokCrossSignalGate:
    config: XaiSearchConfig

    def review(
        self,
        candidate: PolymarketCandidate,
        *,
        queries: tuple[str, ...] | None = None,
    ) -> CrossSignalReview:
        resolved_queries = queries or build_topic_queries(candidate)
        payload = _call_xai(
            config=self.config,
            system_prompt=_system_prompt(),
            user_payload={
                "market_title": candidate.title,
                "market_url": candidate.market_url,
                "source_label": candidate.source_label,
                "queries": list(resolved_queries),
            },
        )
        parsed = _parse_gate_output(payload)
        posts = tuple(
            CrossSignalPost(
                tweet_id=f"grok:{index}",
                author_handle=str(item.get("author_handle", "")).strip(),
                text=str(item.get("text", "")).strip(),
                url=str(item.get("url", "")).strip(),
                spread_score=float(max(100 - index, 1)),
            )
            for index, item in enumerate(parsed["top_5_posts"], start=1)
            if str(item.get("text", "")).strip() or str(item.get("url", "")).strip()
        )
        distinct_accounts = len({post.author_handle.lower() for post in posts if post.author_handle})
        return CrossSignalReview(
            slug=candidate.slug,
            market_title=candidate.title,
            market_url=candidate.market_url,
            source_label=candidate.source_label,
            queries=tuple(resolved_queries),
            is_viral=bool(parsed["is_viral"]),
            reason_if_not_viral=str(parsed["reason_if_not_viral"]).strip(),
            angle_summary=str(parsed["one_line_angle"]).strip(),
            confidence=int(parsed["confidence"]),
            top_posts=posts,
            distinct_post_count=len(posts),
            distinct_account_count=distinct_accounts,
        )

    def evaluate(
        self,
        candidate: PolymarketCandidate,
        *,
        queries: tuple[str, ...] | None = None,
    ) -> CrossSignalAlert | None:
        review = self.review(candidate, queries=queries)
        if not review.is_viral:
            return None
        return CrossSignalAlert(
            topic=review.queries[0] if review.queries else candidate.title,
            market_title=review.market_title,
            market_url=review.market_url,
            source_label=review.source_label,
            queries=review.queries,
            top_posts=review.top_posts,
            angle_summary=review.angle_summary,
            distinct_post_count=review.distinct_post_count,
            distinct_account_count=review.distinct_account_count,
            verification_passed=True,
        )


def _call_xai(*, config: XaiSearchConfig, system_prompt: str, user_payload: dict[str, object]) -> str:
    last_error: Exception | None = None
    for _ in range(config.max_retries + 1):
        body: dict[str, object] = {
            "model": config.model,
            "instructions": system_prompt,
            "input": json.dumps(user_payload, ensure_ascii=False, indent=2),
            "tools": [{"type": "x_search"}],
            "tool_choice": "auto",
        }
        if config.reasoning_effort:
            body["reasoning"] = {"effort": config.reasoning_effort}

        req = request.Request(
            build_endpoint(config.base_url, "responses"),
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.api_key}",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=config.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
            return extract_text_from_response(json.loads(raw), api_mode="responses")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"Grok cross-signal HTTP {exc.code}: {detail}")
        except error.URLError as exc:
            last_error = RuntimeError(f"Grok cross-signal request failed: {exc.reason}")
        except TimeoutError as exc:
            last_error = RuntimeError(f"Grok cross-signal request timed out: {exc}")

    raise last_error or RuntimeError("Grok cross-signal request failed")


def _parse_gate_output(raw_text: str) -> dict[str, object]:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`").replace("json", "", 1).strip()
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        text = text[first:last + 1]
    payload = json.loads(text)
    posts = payload.get("top_5_posts") or []
    if not isinstance(posts, list):
        posts = []
    return {
        "is_viral": bool(payload.get("is_viral")),
        "reason_if_not_viral": str(payload.get("reason_if_not_viral", "")).strip(),
        "top_5_posts": [item for item in posts if isinstance(item, dict)][:5],
        "one_line_angle": str(payload.get("one_line_angle", "")).strip(),
        "confidence": _coerce_confidence(payload.get("confidence", 0)),
    }


def _system_prompt() -> str:
    return (
        "You are a trend monitoring agent.\n"
        "Use x_search to inspect whether the given topic is actually spreading on X.\n"
        "Do not rely on one post only. Look for multiple posts, secondary discussion, meme spread, or quote-tweet compounding.\n"
        "Return strict JSON only with keys is_viral, reason_if_not_viral, top_5_posts, one_line_angle, confidence.\n"
        "top_5_posts must be a list of objects with keys text, url, author_handle, retweet_velocity, secondary_engagement_desc.\n"
        "If the topic is not meaningfully spreading, set is_viral to false."
    )


def _coerce_confidence(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).strip().lower()
    if not text:
        return 0
    if text.isdigit():
        return int(text)
    if text == "high":
        return 85
    if text == "medium":
        return 60
    if text == "low":
        return 30
    return 0
