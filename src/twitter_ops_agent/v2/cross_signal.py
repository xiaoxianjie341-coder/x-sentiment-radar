from __future__ import annotations

from dataclasses import dataclass

from twitter_ops_agent.domain.models import CrossSignalAlert


@dataclass(slots=True)
class CrossSignalRunReport:
    candidate_count: int
    passed_count: int
    topics: tuple[CrossSignalAlert, ...] = ()


@dataclass(slots=True)
class CrossSignalOrchestrator:
    scout: object
    gate: object

    def run(self) -> CrossSignalRunReport:
        candidates = list(self.scout.run())
        topics = tuple(
            alert
            for candidate in candidates
            for alert in [self.gate.evaluate(candidate)]
            if alert is not None
        )
        return CrossSignalRunReport(
            candidate_count=len(candidates),
            passed_count=len(topics),
            topics=topics,
        )
