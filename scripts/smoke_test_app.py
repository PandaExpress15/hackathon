from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def fetch(url: str, timeout: float = 2.0) -> bytes:
    with urlopen(url, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"Unexpected HTTP status {response.status} for {url}")
        return response.read()


def main() -> int:
    port = free_port()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env["CAREERPROOF_PORT"] = str(port)
    process = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.time() + 30
        health = None
        while time.time() < deadline:
            try:
                health = json.loads(fetch(f"http://127.0.0.1:{port}/api/health").decode("utf-8"))
                break
            except (URLError, ConnectionError, TimeoutError, json.JSONDecodeError):
                time.sleep(0.25)
        if health is None:
            output = process.stdout.read() if process.stdout else ""
            raise RuntimeError(f"Application did not become ready.\n{output}")
        page = fetch(f"http://127.0.0.1:{port}/").decode("utf-8")
        if health.get("status") != "ok" or health.get("stats", {}).get("occupations") != 830:
            raise RuntimeError(f"Unexpected health payload: {health}")
        for marker in ["CareerProof AI", "Real career data", "Official sources only"]:
            if marker not in page:
                raise RuntimeError(f"Missing page marker: {marker}")
        print(f"PASS: CareerProof launched on port {port}")
        print("PASS: health endpoint returned 830 detailed occupations")
        print("PASS: rendered product shell contains official-data markers")
        return 0
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
