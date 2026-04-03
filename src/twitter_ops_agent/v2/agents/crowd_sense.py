from __future__ import annotations

from dataclasses import dataclass

from twitter_ops_agent.domain.models import CrowdSummary
from twitter_ops_agent.research.crowd_context import CrowdContextService, heuristic_crowd_summary
from twitter_ops_agent.v2.contracts import HydratedSeed


@dataclass(slots=True)
class CrowdSenseAgent:
    crowd_context: CrowdContextService
    signal_min_views: int = 0
    signal_min_likes: int = 0
    signal_min_replies: int = 0

    def run(self, seed: HydratedSeed):
        summary = self.crowd_context.build(tweet_id=seed.seed.tweet_id, seed_text=seed.source_text)
        signal_limit = max(1, int(getattr(self.crowd_context, "top_signal_count", 10)))
        filtered = [
            signal
            for signal in summary.top_signals
            if not _is_noise_signal(signal, seed, self)
        ][:signal_limit]
        if not filtered:
            return summary
        if getattr(self.crowd_context, "summarizer", None) is not None:
            return CrowdSummary(
                sentiment_summary=summary.sentiment_summary,
                key_points=summary.key_points,
                suggested_angles=summary.suggested_angles,
                top_signals=tuple(filtered),
                source_label=summary.source_label,
            )
        rebuilt = heuristic_crowd_summary(
            seed_text=seed.source_text,
            thread=[],
            signals=filtered,
            source_label=summary.source_label,
        )
        return CrowdSummary(
            sentiment_summary=rebuilt.sentiment_summary,
            key_points=rebuilt.key_points,
            suggested_angles=rebuilt.suggested_angles,
            top_signals=tuple(filtered),
            source_label=summary.source_label,
        )


def _is_noise_signal(signal, seed: HydratedSeed, agent: CrowdSenseAgent) -> bool:
    text = signal.text.lower()
    if signal.author_handle.lower() == seed.seed.author_handle.lower():
        return True
    if signal.author_handle.lower() in {"grok", "threadreaderapp"}:
        return True
    if "@threadreaderapp" in text or "unroll" in text:
        return True
    normalized = " ".join(signal.text.split())
    if len(normalized) < 24:
        return True
    cleaned = _strip_mentions_and_urls(normalized)
    if len(cleaned) < 16:
        return True
    generic_noise_markers = (
        "好文",
        "求推荐",
        "推荐下",
        "可以转载",
        "转载",
        "unroll",
        "threadreader",
    )
    if any(marker in signal.text for marker in generic_noise_markers):
        return True
    return False


def _strip_mentions_and_urls(text: str) -> str:
    words = []
    for token in text.split():
        if token.startswith("@"):
            continue
        if token.startswith("http://") or token.startswith("https://"):
            continue
        words.append(token)
    return " ".join(words).strip()
