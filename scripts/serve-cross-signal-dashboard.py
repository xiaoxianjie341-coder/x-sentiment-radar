from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT_DIR = Path(__file__).resolve().parents[1]
TAG = "# x-sentiment-radar cross-signal"
REVIEW_ALL_PID = ROOT_DIR / "data" / "cross-signal" / "review_all.pid"
REVIEW_ALL_LOG = ROOT_DIR / "data" / "cross-signal" / "review_all.log"


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


def _job_running(pid_file: Path) -> bool:
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text().strip())
    except ValueError:
        pid_file.unlink(missing_ok=True)
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        pid_file.unlink(missing_ok=True)
        return False


def _start_review_all_job() -> dict[str, object]:
    REVIEW_ALL_PID.parent.mkdir(parents=True, exist_ok=True)
    if _job_running(REVIEW_ALL_PID):
        return {"started": False, "running": True}

    with REVIEW_ALL_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"\n=== review_all started at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    log_handle = REVIEW_ALL_LOG.open("a", encoding="utf-8")
    process = subprocess.Popen(
        [str(ROOT_DIR / "scripts" / "review-all-breaking-now.sh")],
        cwd=ROOT_DIR,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    REVIEW_ALL_PID.write_text(str(process.pid), encoding="utf-8")
    return {"started": True, "running": True}


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
                    "review_all_running": _job_running(REVIEW_ALL_PID),
                }
            )
            return
        if parsed.path == "/api/job-status":
            self._send_json(
                {
                    "review_all_running": _job_running(REVIEW_ALL_PID),
                    "latest": _load_latest(),
                }
            )
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/run-check":
            payload = _read_json(self)
            mode = str(payload.get("mode", "incremental"))
            if mode == "review_all":
                status = _start_review_all_job()
                self._send_json(
                    {
                        "ok": True,
                        "mode": mode,
                        **status,
                        "latest": _load_latest(),
                    }
                )
                return
            script_name = "run-cross-signal-grok.sh"
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
