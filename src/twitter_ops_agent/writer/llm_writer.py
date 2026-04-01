from __future__ import annotations

from dataclasses import dataclass
import json
from urllib import error, request

from twitter_ops_agent.domain.models import DraftTweet, ResearchCard, StyleExample, StyleProfile


@dataclass(slots=True)
class LLMWriterConfig:
    base_url: str
    api_key: str
    model: str
    api_mode: str = "responses"
    reasoning_effort: str = ""
    timeout_seconds: float = 45.0


@dataclass(slots=True)
class LLMStyleWriter:
    config: LLMWriterConfig

    def generate(
        self,
        *,
        card: ResearchCard,
        style_examples: list[StyleExample],
        style_profile: StyleProfile | None,
    ) -> DraftTweet:
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(card, style_examples, style_profile)
        raw_text = call_openai_compatible_api(
            config=self.config,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        payload = parse_llm_output(raw_text)
        return DraftTweet(
            draft_id=f"{card.event_id}:draft-1",
            track=card.track,
            tweet_text=payload["tweet_text"],
            translation_text=payload["translation_text"],
            reasoning_outline=payload["reasoning_outline"],
            source_post_ids=(card.event_id,),
            writer_name="llm_writer",
            writer_model=self.config.model,
        )


def build_system_prompt() -> str:
    return (
        "You write X quote-tweets in the user's learned house style.\n"
        "Use the provided style examples as the primary style reference.\n"
        "Do not output generic scaffolding labels like 'Background:' or 'Why this matters:'.\n"
        "Write with punchy momentum, short paragraphs, and a strong opening hook.\n"
        "Expand the headline into consequence, tension, or judgment.\n"
        "Use only facts provided in the source headline, research card, and examples.\n"
        "Do not invent numbers, dates, or claims that are not in the prompt.\n"
        "Also provide a natural simplified-Chinese translation with matching meaning and paragraphing.\n"
        "Return JSON only with keys tweet_text, translation_text, and reasoning_outline."
    )


def build_user_prompt(
    card: ResearchCard,
    style_examples: list[StyleExample],
    style_profile: StyleProfile | None,
) -> str:
    examples = []
    for item in style_examples[:5]:
        examples.append(
            {
                "target_text": item.target_text,
                "source_text": item.source_text,
                "track": item.track,
            }
        )

    payload = {
        "task": "Write one X post draft in the learned creator style.",
        "requirements": [
            "Open with a strong hook that sounds like the examples.",
            "Turn the headline into a broader interpretation or consequence.",
            "Avoid rigid explainer labels and avoid sounding like a report.",
            "Stay close to the style examples in cadence and tone.",
            "Keep it ready for a quote-tweet workflow.",
        ],
        "research_card": {
            "event_title": card.event_title,
            "seed_news_post": card.seed_news_post,
            "summary": card.one_paragraph_summary,
            "timeline": list(card.timeline),
            "why_it_matters": card.why_it_matters,
            "likely_implications": list(card.likely_implications),
            "crowd_sentiment_summary": card.crowd_sentiment_summary,
            "crowd_key_points": list(card.crowd_key_points),
            "crowd_suggested_angles": list(card.crowd_suggested_angles),
            "crowd_top_signals": [
                {
                    "author": signal.author_handle,
                    "text": signal.text,
                    "likes": signal.likes,
                    "replies": signal.replies,
                    "views": signal.views,
                }
                for signal in card.crowd_top_signals[:5]
            ],
            "source_links": list(card.source_links),
            "draft_angles": list(card.draft_angles),
        },
        "style_profile": {
            "dominant_track": style_profile.dominant_track if style_profile else None,
            "common_openers": list(style_profile.common_openers) if style_profile else [],
            "common_phrases": list(style_profile.common_phrases) if style_profile else [],
            "avg_line_count": style_profile.avg_line_count if style_profile else 0,
            "avg_char_count": style_profile.avg_char_count if style_profile else 0,
        },
        "style_examples": examples,
        "output_format": {
            "tweet_text": "final English X post only",
            "translation_text": "natural simplified-Chinese translation with similar paragraph breaks",
            "reasoning_outline": "short outline like Hook -> Reframe -> Judgment -> Closing",
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def call_openai_compatible_api(
    *,
    config: LLMWriterConfig,
    system_prompt: str,
    user_prompt: str,
) -> str:
    if config.api_mode == "chat_completions":
        body = {
            "model": config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
    else:
        body = {
            "model": config.model,
            "instructions": system_prompt,
            "input": user_prompt,
        }
        if config.reasoning_effort:
            body["reasoning"] = {"effort": config.reasoning_effort}

    payload = json.dumps(body).encode("utf-8")
    req = request.Request(
        build_endpoint(config.base_url, config.api_mode),
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=config.timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM writer HTTP {exc.code}: {body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"LLM writer request failed: {exc.reason}") from exc

    data = json.loads(raw)
    return extract_text_from_response(data, api_mode=config.api_mode)


def build_endpoint(base_url: str, api_mode: str) -> str:
    trimmed = base_url.rstrip("/")
    if trimmed.endswith("/responses") or trimmed.endswith("/chat/completions"):
        return trimmed
    suffix = "chat/completions" if api_mode == "chat_completions" else "responses"
    if trimmed.endswith("/v1"):
        return f"{trimmed}/{suffix}"
    return f"{trimmed}/v1/{suffix}"


def extract_text_from_response(data: dict, api_mode: str) -> str:
    if api_mode == "chat_completions":
        choices = data.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            content = message.get("content")
            if isinstance(content, str):
                return content
        return ""

    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    chunks: list[str] = []
    for item in data.get("output") or []:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            chunks.append(item["text"])
        for part in item.get("content") or [] if isinstance(item, dict) else []:
            if isinstance(part, dict):
                if isinstance(part.get("text"), str):
                    chunks.append(part["text"])
                if isinstance(part.get("output_text"), str):
                    chunks.append(part["output_text"])
    return "\n".join(part for part in chunks if part).strip()


def parse_llm_output(raw_text: str) -> dict[str, str]:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`").replace("json", "", 1).strip()

    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        text = text[first:last + 1]

    data = json.loads(text)
    tweet_text = str(data.get("tweet_text") or "").strip()
    translation_text = str(data.get("translation_text") or "").strip()
    reasoning_outline = str(data.get("reasoning_outline") or "").strip()
    if not tweet_text:
        raise RuntimeError("LLM writer returned empty tweet_text")
    if not translation_text:
        raise RuntimeError("LLM writer returned empty translation_text")
    if not reasoning_outline:
        reasoning_outline = "LLM style draft"
    return {
        "tweet_text": tweet_text,
        "translation_text": translation_text,
        "reasoning_outline": reasoning_outline,
    }
