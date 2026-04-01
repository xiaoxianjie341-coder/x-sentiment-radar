from __future__ import annotations

import re


def classify_track(text: str, source_handle: str | None) -> str | None:
    ai_keywords = {"ai", "openai", "anthropic", "model", "agent", "llm", "inference"}
    crypto_keywords = {"crypto", "bitcoin", "btc", "ethereum", "eth", "solana", "token", "etf"}

    haystack = f"{text} {source_handle or ''}".lower()
    words = set(re.findall(r"[a-z0-9_]+", haystack))
    if ai_keywords & words:
        return "AI"
    if crypto_keywords & words:
        return "Crypto"
    return None
