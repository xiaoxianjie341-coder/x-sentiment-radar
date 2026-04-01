from twitter_ops_agent.config import load_settings
from twitter_ops_agent.doctor import run_doctor


class _StubCaptureService:
    def __init__(self, selected_backend: str) -> None:
        self._selected_backend = selected_backend

    def inspect_health(self, settings):
        return {
            "selected_capture_backend": self._selected_backend,
            "capture_reason": "forced by test",
            "twscrape_auth_ok": self._selected_backend == "twscrape",
        }


def make_capture_service(selected_backend: str) -> _StubCaptureService:
    return _StubCaptureService(selected_backend=selected_backend)


def test_run_doctor_reports_selected_capture_backend_and_outputs():
    settings = load_settings(config_path=None, env={})

    report = run_doctor(
        settings=settings,
        capture_service=make_capture_service(selected_backend="x_fetcher_camofox"),
    )

    assert report.selected_capture_backend == "x_fetcher_camofox"
    assert report.obsidian_root.name == "推特运营Agent"
    assert report.research_login == "Trieu"
