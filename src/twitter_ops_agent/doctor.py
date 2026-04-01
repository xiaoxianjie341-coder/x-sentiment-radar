from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from twitter_ops_agent.config import AppSettings


@dataclass(slots=True)
class DoctorReport:
    selected_capture_backend: str
    capture_reason: str
    twscrape_auth_ok: bool
    research_login: str
    obsidian_root: Path
    sqlite_db: Path


def run_doctor(settings: AppSettings, capture_service: Any | None = None) -> DoctorReport:
    health = _inspect_capture_service(capture_service=capture_service, settings=settings)

    return DoctorReport(
        selected_capture_backend=str(health["selected_capture_backend"]),
        capture_reason=str(health["capture_reason"]),
        twscrape_auth_ok=bool(health["twscrape_auth_ok"]),
        research_login=settings.opencli_profile_name,
        obsidian_root=settings.obsidian_root,
        sqlite_db=settings.sqlite_db,
    )


def _inspect_capture_service(
    capture_service: Any | None,
    settings: AppSettings,
) -> Mapping[str, Any]:
    if capture_service is None:
        return {
            "selected_capture_backend": "x_fetcher_camofox",
            "capture_reason": "bootstrap default until capture adapters are configured",
            "twscrape_auth_ok": False,
        }

    if hasattr(capture_service, "inspect_health"):
        result = capture_service.inspect_health(settings)
        if isinstance(result, Mapping):
            return result

    raise TypeError("capture_service must expose inspect_health(settings) -> Mapping")
