from __future__ import annotations

from dataclasses import dataclass
import json

from twitter_ops_agent.discovery.attentionvc import AttentionTweet, AttentionVCArticleClient, build_search_query
from twitter_ops_agent.domain.models import CrowdSignal, CrowdSummary
from twitter_ops_agent.writer.llm_writer import LLMWriterConfig, call_openai_compatible_api

SKEPTICAL_MARKERS = ("scam", "fake", "cope", "doubt", "why", "risk", "质疑", "怀疑", "割", "泡沫", "风险")
FEAR_MARKERS = ("fear", "panic", "dump", "crash", "bear", "担心", "恐慌", "暴跌", "害怕")
POSITIVE_MARKERS = ("bull", "long", "buy", "good", "great", "alpha", "机会", "看多", "利好", "牛", "冲")
EMOTION_ORDER = ("质疑/求证", "担忧/风险", "兴奋/机会", "中性/信息补充")


@dataclass(slots=True)
class CrowdContextService:
    client: AttentionVCArticleClient
    reply_sample_limit: int = 20
    top_signal_count: int = 10
    search_fallback_limit: int = 8
    summarizer: object | None = None

    def build(self, *, tweet_id: str, seed_text: str) -> CrowdSummary:
        thread = self.client.tweet_thread(tweet_id=tweet_id)
        replies = self.client.tweet_replies(tweet_id=tweet_id, limit=self.reply_sample_limit)
        source_labels: list[str] = []
        candidate_limit = max(self.top_signal_count * 3, 20)
        signals = _rank_signals(replies, limit=candidate_limit, source_type="reply")
        if signals:
            source_labels.append("评论区")

        thread_replies = [tweet for tweet in thread if tweet.tweet_id != tweet_id]
        if len(signals) < self.top_signal_count and thread_replies:
            thread_signals = _rank_signals(thread_replies, limit=candidate_limit, source_type="thread")
            signals = _merge_signals(signals, thread_signals, limit=candidate_limit)
            if thread_signals:
                source_labels.append("作者线程")

        if len(signals) < self.top_signal_count:
            fallback_query = build_search_query(seed_text)
            related = _filter_related_discussion(
                seed_text=seed_text,
                tweets=[
                    tweet
                    for tweet in self.client.search_tweets(
                        query=fallback_query,
                        limit=max(self.search_fallback_limit, candidate_limit),
                    )
                    if tweet.tweet_id != tweet_id
                ],
            )
            related_signals = _rank_signals(related, limit=candidate_limit, source_type="discussion")
            signals = _merge_signals(signals, related_signals, limit=candidate_limit)
            if related_signals:
                source_labels.append("相关讨论")

        source_label = " + ".join(dict.fromkeys(source_labels)) or "评论区"

        if self.summarizer is not None and signals:
            try:
                return self.summarizer.summarize(
                    seed_text=seed_text,
                    thread=thread,
                    signals=signals,
                    source_label=source_label,
                )
            except Exception:
                pass

        return heuristic_crowd_summary(seed_text=seed_text, thread=thread, signals=signals, source_label=source_label)


@dataclass(slots=True)
class LLMCrowdSummarizer:
    config: LLMWriterConfig

    def summarize(
        self,
        *,
        seed_text: str,
        thread: list[AttentionTweet],
        signals: list[CrowdSignal],
        source_label: str,
    ) -> CrowdSummary:
        system_prompt = (
            "You are analyzing X/Twitter audience reaction for a content operator.\n"
            "Return JSON only with keys sentiment_summary, key_points, suggested_angles.\n"
            "sentiment_summary should be concise Chinese.\n"
            "key_points should be a list of 3-5 short Chinese bullets summarizing what people actually care about.\n"
            "suggested_angles should be a list of 2-3 short Chinese post angles.\n"
            "Stay grounded in the provided source tweet, thread, and audience signals only."
        )
        payload = {
            "source_tweet": seed_text,
            "source_label": source_label,
            "thread": [
                {
                    "author": tweet.author_handle,
                    "text": tweet.text,
                    "likes": tweet.likes,
                    "replies": tweet.replies,
                    "views": tweet.views,
                }
                for tweet in thread[:5]
            ],
            "top_signals": [
                {
                    "author": signal.author_handle,
                    "text": signal.text,
                    "likes": signal.likes,
                    "replies": signal.replies,
                    "views": signal.views,
                    "source_type": signal.source_type,
                }
                for signal in signals
            ],
        }
        raw = call_openai_compatible_api(
            config=self.config,
            system_prompt=system_prompt,
            user_prompt=json.dumps(payload, ensure_ascii=False, indent=2),
        )
        parsed = _parse_summary_output(raw)
        return CrowdSummary(
            sentiment_summary=parsed["sentiment_summary"],
            key_points=parsed["key_points"],
            suggested_angles=parsed["suggested_angles"],
            top_signals=tuple(signals),
            source_label=source_label,
        )


def heuristic_crowd_summary(
    *,
    seed_text: str,
    thread: list[AttentionTweet],
    signals: list[CrowdSignal],
    source_label: str,
) -> CrowdSummary:
    if not signals:
        return CrowdSummary(
            sentiment_summary=f"{source_label}暂时没有抓到足够稳定的高信号内容，更适合先观察，不建议强写结论。",
            key_points=("暂无稳定高信号观点，建议手动点回原帖再判断。",),
            suggested_angles=("先写信息澄清，不要急着下重判断。",),
            top_signals=(),
            source_label=source_label,
        )

    emotion_counts = summarize_signal_emotions(signals)
    skeptical = emotion_counts["质疑/求证"]
    fear = emotion_counts["担忧/风险"]
    positive = emotion_counts["兴奋/机会"]

    if skeptical >= positive and skeptical >= fear:
        mood = "评论区更偏质疑和求证，大家不是没兴趣，而是对信息可信度和后续兑现更敏感。"
    elif fear >= positive:
        mood = "评论区更偏谨慎和风险导向，大家最在意的不是 headline 本身，而是后续会不会扩散。"
    else:
        mood = "评论区整体偏兴奋和机会导向，大家更在意这件事会不会继续发酵，以及谁会成为受益方。"

    key_points = tuple(
        _compress_signal_text(signal.text)
        for signal in signals[: min(len(signals), 5)]
    )
    suggested_angles = (
        "先写大家最关心的那个判断，不要只复述新闻。",
        "把评论区最强分歧点提出来，再补你自己的判断。",
    )
    if thread and len(thread) > 1:
        suggested_angles += ("可以顺手带一句作者自己在线程里的补充，这样内容会更完整。",)

    return CrowdSummary(
        sentiment_summary=mood,
        key_points=key_points,
        suggested_angles=suggested_angles[:3],
        top_signals=tuple(signals),
        source_label=source_label,
    )


def _rank_signals(
    tweets: list[AttentionTweet],
    *,
    limit: int,
    source_type: str,
) -> list[CrowdSignal]:
    ranked: list[CrowdSignal] = []
    seen_texts: set[str] = set()
    for tweet in tweets:
        text = tweet.text.strip()
        if len(text) < 20:
            continue
        normalized = " ".join(text.split())
        if normalized in seen_texts:
            continue
        seen_texts.add(normalized)
        score = (
            tweet.likes * 10
            + tweet.replies * 8
            + tweet.bookmarks * 5
            + min(tweet.views / 100.0, 100.0)
        )
        ranked.append(
            CrowdSignal(
                tweet_id=tweet.tweet_id,
                author_handle=tweet.author_handle,
                author_name=tweet.author_name,
                text=text,
                url=tweet.url,
                likes=tweet.likes,
                replies=tweet.replies,
                views=tweet.views,
                bookmarks=tweet.bookmarks,
                signal_score=round(score, 2),
                source_type=source_type,
            )
        )
    ranked.sort(key=lambda item: (item.views, item.likes, item.replies, item.bookmarks, item.signal_score), reverse=True)
    return ranked[:limit]


def classify_signal_emotion(text: str) -> str:
    lowered = text.lower()
    skeptical_score = sum(1 for token in SKEPTICAL_MARKERS if token in lowered)
    fear_score = sum(1 for token in FEAR_MARKERS if token in lowered)
    positive_score = sum(1 for token in POSITIVE_MARKERS if token in lowered)

    if skeptical_score >= fear_score and skeptical_score >= positive_score and skeptical_score > 0:
        return "质疑/求证"
    if fear_score >= positive_score and fear_score > 0:
        return "担忧/风险"
    if positive_score > 0:
        return "兴奋/机会"
    return "中性/信息补充"


def summarize_signal_emotions(signals: list[CrowdSignal] | tuple[CrowdSignal, ...]) -> dict[str, int]:
    counts = {label: 0 for label in EMOTION_ORDER}
    for signal in signals:
        counts[classify_signal_emotion(signal.text)] += 1
    return counts


def group_signals_by_emotion(
    signals: list[CrowdSignal] | tuple[CrowdSignal, ...],
) -> tuple[tuple[str, tuple[CrowdSignal, ...]], ...]:
    grouped: dict[str, list[CrowdSignal]] = {label: [] for label in EMOTION_ORDER}
    for signal in signals:
        grouped[classify_signal_emotion(signal.text)].append(signal)
    return tuple((label, tuple(grouped[label])) for label in EMOTION_ORDER)


def _merge_signals(
    primary: list[CrowdSignal],
    secondary: list[CrowdSignal],
    *,
    limit: int,
) -> list[CrowdSignal]:
    merged: list[CrowdSignal] = []
    seen_ids: set[str] = set()
    for signal in [*primary, *secondary]:
        if signal.tweet_id in seen_ids:
            continue
        seen_ids.add(signal.tweet_id)
        merged.append(signal)
        if len(merged) >= limit:
            break
    return merged


def _compress_signal_text(text: str) -> str:
    compact = " ".join(text.split())
    if len(compact) <= 120:
        return compact
    return compact[:117] + "..."


def _parse_summary_output(raw_text: str) -> dict[str, tuple[str, ...] | str]:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`").replace("json", "", 1).strip()
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        text = text[first:last + 1]

    payload = json.loads(text)
    sentiment_summary = str(payload.get("sentiment_summary") or "").strip()
    key_points = tuple(str(item).strip() for item in payload.get("key_points") or [] if str(item).strip())
    suggested_angles = tuple(
        str(item).strip() for item in payload.get("suggested_angles") or [] if str(item).strip()
    )
    if not sentiment_summary:
        raise RuntimeError("Crowd summarizer returned empty sentiment_summary")
    return {
        "sentiment_summary": sentiment_summary,
        "key_points": key_points,
        "suggested_angles": suggested_angles,
    }


def _filter_related_discussion(seed_text: str, tweets: list[AttentionTweet]) -> list[AttentionTweet]:
    first_line = seed_text.strip().splitlines()[0]
    normalized_seed = " ".join(first_line.split())
    seed_tokens = {token.lower() for token in normalized_seed.split() if len(token) >= 4}
    cjk_anchor = normalized_seed[:8] if _contains_cjk(normalized_seed) else ""

    filtered: list[AttentionTweet] = []
    for tweet in tweets:
        candidate_text = " ".join(tweet.text.split())
        if cjk_anchor and cjk_anchor in candidate_text:
            filtered.append(tweet)
            continue
        candidate_tokens = {token.lower() for token in candidate_text.split() if len(token) >= 4}
        if seed_tokens and len(seed_tokens & candidate_tokens) >= 2:
            filtered.append(tweet)
    return filtered


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)
