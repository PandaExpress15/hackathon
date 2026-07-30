#!/usr/bin/env python3
"""Launch CareerProof AI on a temporary local port and verify its HTTP response."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STARTUP_TIMEOUT_SECONDS = 60
POLL_INTERVAL_SECONDS = 0.5
EXPECTED_MARKERS = ("CareerProof AI", "Ask the job market. See the proof.")


def free_local_port() -> int:
    """Reserve an available loopback port long enough to choose it for the smoke test."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def tail(path: Path, lines: int = 30) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(content[-lines:])


def main() -> int:
    port = free_local_port()
    url = f"http://127.0.0.1:{port}/"
    env = os.environ.copy()
    env.update(
        {
            "CAREERPROOF_SERVER_NAME": "127.0.0.1",
            "CAREERPROOF_SERVER_PORT": str(port),
            "CAREERPROOF_DEBUG": "false",
            "PYTHONPATH": str(PROJECT_ROOT / "src")
            + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""),
        }
    )

    with tempfile.TemporaryDirectory(prefix="careerproof-smoke-") as temp_dir:
        log_path = Path(temp_dir) / "app.log"
        with log_path.open("w", encoding="utf-8") as log_handle:
            process = subprocess.Popen(
                [sys.executable, "app.py"],
                cwd=PROJECT_ROOT,
                env=env,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
            )

        deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
        last_error = "No HTTP response received."
        try:
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    print("Application process exited before becoming ready.")
                    print(tail(log_path))
                    return 1
                try:
                    with urllib.request.urlopen(url, timeout=3) as response:
                        body = response.read(2_000_000).decode("utf-8", errors="replace")
                        if response.status != 200:
                            last_error = f"HTTP status {response.status}"
                        elif not any(marker in body for marker in EXPECTED_MARKERS):
                            last_error = "HTTP 200 received, but the CareerProof title marker was missing."
                        else:
                            print("CareerProof AI application smoke test: PASS")
                            print(f"HTTP 200 from {url}")
                            print("The launch page contained the expected CareerProof title marker.")
                            return 0
                except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
                time.sleep(POLL_INTERVAL_SECONDS)

            print("Application did not become ready before the timeout.")
            print(last_error)
            print(tail(log_path))
            return 1
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)


if __name__ == "__main__":
    raise SystemExit(main())
