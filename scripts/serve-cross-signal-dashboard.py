from __future__ import annotations

import json
import os
import subprocess
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT_DIR = Path(__file__).resolve().parents[1]
TAG = "# x-sentiment-radar cross-signal"


def _read_json(request: SimpleHTTPRequestHandler) -> dict[str, object]:
    length = int(request.headers.get("Content-Length", "0") or 0)
    if length <= 0:
        return {}
    raw = request.rfile.read(length).decode("utf-8")
    return json.loads(raw) if raw.strip() else {}


def _run_script(script_name: str, *, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(ROOT_DIR / "scripts" / script_name)],
        cwd=ROOT_DIR,
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def _schedule_enabled() -> bool:
    result = subprocess.run(["crontab", "-l"], text=True, capture_output=True)
    return TAG in (result.stdout or "")


def _load_latest() -> dict[str, object]:
    latest = ROOT_DIR / "data" / "cross-signal" / "latest.json"
    if not latest.exists():
        return {}
    return json.loads(latest.read_text(encoding="utf-8"))


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT_DIR), **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/meta":
            self._send_json(
                {
                    "schedule_enabled": _schedule_enabled(),
                    "latest_path": "/data/cross-signal/latest.json",
                }
            )
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/run-check":
            payload = _read_json(self)
            mode = str(payload.get("mode", "incremental"))
            script_name = "run-cross-signal-grok.sh" if mode == "incremental" else "review-all-breaking-now.sh"
            result = _run_script(script_name, timeout=1800 if mode == "review_all" else 600)
            self._send_json(
                {
                    "ok": result.returncode == 0,
                    "mode": mode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "latest": _load_latest(),
                },
                status=HTTPStatus.OK if result.returncode == 0 else HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return

        if parsed.path == "/api/toggle-schedule":
            payload = _read_json(self)
            enabled = bool(payload.get("enabled"))
            script_name = "install-cross-signal-cron.sh" if enabled else "uninstall-cross-signal-cron.sh"
            result = _run_script(script_name, timeout=60)
            self._send_json(
                {
                    "ok": result.returncode == 0,
                    "schedule_enabled": _schedule_enabled(),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
                status=HTTPStatus.OK if result.returncode == 0 else HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")

    def _send_json(self, payload: dict[str, object], *, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
    print(f"Serving cross-signal dashboard at http://127.0.0.1:{port}/frontend/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
