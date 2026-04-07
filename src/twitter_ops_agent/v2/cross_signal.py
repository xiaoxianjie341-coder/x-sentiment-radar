from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from twitter_ops_agent.domain.models import CrossSignalAlert, CrossSignalCandidate


@dataclass(slots=True)
class CrossSignalRunReport:
    candidate_count: int
    new_candidate_count: int
    passed_count: int
    candidates: tuple[CrossSignalCandidate, ...] = ()
    new_candidates: tuple[CrossSignalCandidate, ...] = ()
    topics: tuple[CrossSignalAlert, ...] = ()


@dataclass(slots=True)
class CrossSignalStateStore:
    path: Path
    state_size: int = 300

    def load_seen(self) -> tuple[str, ...]:
        if not self.path.exists():
            return ()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return ()
        if not isinstance(payload, list):
            return ()
        return tuple(str(item).strip() for item in payload if str(item).strip())

    def save_seen(self, seen: tuple[str, ...]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        limited = tuple(seen[: self.state_size])
        self.path.write_text(json.dumps(list(limited), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@dataclass(slots=True)
class CrossSignalOrchestrator:
    scout: object
    gate: object
    state_store: object | None = None

    def run(self) -> CrossSignalRunReport:
        candidates = list(self.scout.run())
        seen = self.state_store.load_seen() if self.state_store is not None else ()
        seen_set = set(seen)
        new_candidates = [candidate for candidate in candidates if getattr(candidate, "slug", "") not in seen_set]
        topics = tuple(
            alert
            for candidate in new_candidates
            for alert in [self.gate.evaluate(candidate)]
            if alert is not None
        )
        all_candidate_previews = tuple(_to_candidate_preview(candidate) for candidate in candidates)
        new_candidate_previews = tuple(_to_candidate_preview(candidate) for candidate in new_candidates)
        if self.state_store is not None:
            merged = _merge_seen(
                [getattr(candidate, "slug", "") for candidate in candidates],
                seen,
            )
            self.state_store.save_seen(merged)
        return CrossSignalRunReport(
            candidate_count=len(candidates),
            new_candidate_count=len(new_candidates),
            passed_count=len(topics),
            candidates=all_candidate_previews,
            new_candidates=new_candidate_previews,
            topics=topics,
        )


def _merge_seen(current_ids: list[str], previous_seen: tuple[str, ...]) -> tuple[str, ...]:
    merged: list[str] = []
    seen: set[str] = set()
    for item in [*previous_seen, *current_ids]:
        normalized = str(item).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)
    return tuple(merged)


def _to_candidate_preview(candidate: object) -> CrossSignalCandidate:
    return CrossSignalCandidate(
        slug=str(getattr(candidate, "slug", "")).strip(),
        title=str(getattr(candidate, "title", "")).strip(),
        market_url=str(getattr(candidate, "market_url", "")).strip(),
        source_label=str(getattr(candidate, "source_label", "")).strip(),
        category_slug=str(getattr(candidate, "category_slug", "")).strip(),
        secondary_category_slug=str(getattr(candidate, "secondary_category_slug", "")).strip(),
        volume_24h=float(getattr(candidate, "volume_24h", 0.0) or 0.0),
        liquidity=float(getattr(candidate, "liquidity", 0.0) or 0.0),
    )
