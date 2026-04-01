from __future__ import annotations

from dataclasses import dataclass
import json

from twitter_ops_agent.discovery.attentionvc import AttentionTweet, AttentionVCArticleClient, build_search_query
from twitter_ops_agent.domain.models import CrowdSignal, CrowdSummary
from twitter_ops_agent.writer.llm_writer import LLMWriterConfig, call_openai_compatible_api


@dataclass(slots=True)
class CrowdContextService:
    client: AttentionVCArticleClient
    reply_sample_limit: int = 20
    top_signal_count: int = 5
    search_fallback_limit: int = 8
    summarizer: object | None = None

    def build(self, *, tweet_id: str, seed_text: str) -> CrowdSummary:
        thread = self.client.tweet_thread(tweet_id=tweet_id)
        replies = self.client.tweet_replies(tweet_id=tweet_id, limit=self.reply_sample_limit)
        source_label = "评论区"
        signals = _rank_signals(replies, limit=self.top_signal_count, source_type="reply")

        if not signals:
            thread_replies = [tweet for tweet in thread if tweet.tweet_id != tweet_id]
            signals = _rank_signals(thread_replies, limit=self.top_signal_count, source_type="thread")
            source_label = "作者线程"

        if not signals:
            fallback_query = build_search_query(seed_text)
            related = _filter_related_discussion(
                seed_text=seed_text,
                tweets=[
                    tweet
                    for tweet in self.client.search_tweets(query=fallback_query, limit=self.search_fallback_limit)
                    if tweet.tweet_id != tweet_id
                ],
            )
            signals = _rank_signals(related, limit=self.top_signal_count, source_type="discussion")
            source_label = "相关讨论"

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

    positive_markers = ("bull", "long", "buy", "good", "great", "alpha", "机会", "看多", "利好", "牛", "冲")
    skeptical_markers = ("scam", "fake", "cope", "doubt", "why", "risk", "质疑", "怀疑", "割", "泡沫", "风险")
    fear_markers = ("fear", "panic", "dump", "crash", "bear", "担心", "恐慌", "暴跌", "害怕")

    positive = skeptical = fear = 0
    for signal in signals:
        lowered = signal.text.lower()
        if any(token in lowered for token in positive_markers):
            positive += 1
        if any(token in lowered for token in skeptical_markers):
            skeptical += 1
        if any(token in lowered for token in fear_markers):
            fear += 1

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
    ranked.sort(key=lambda item: (item.signal_score, item.likes, item.replies, item.views), reverse=True)
    return ranked[:limit]


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
