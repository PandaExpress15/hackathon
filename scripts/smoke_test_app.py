from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def fetch(url: str, timeout: float = 4.0) -> bytes:
    with urlopen(url, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"Unexpected HTTP status {response.status} for {url}")
        return response.read()


def post_json(url: str, payload: dict, timeout: float = 8.0) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return json.loads(fetch_request(request, timeout).decode("utf-8"))


def fetch_request(request: Request, timeout: float) -> bytes:
    with urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"Unexpected HTTP status {response.status} for {request.full_url}")
        return response.read()


def main() -> int:
    port = free_port()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PORT"] = str(port)
    process = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.time() + 40
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
        diagnostic = json.loads(fetch(f"http://127.0.0.1:{port}/api/diagnostic").decode("utf-8"))
        universe = json.loads(fetch(f"http://127.0.0.1:{port}/api/universe?limit=4").decode("utf-8"))
        path = post_json(f"http://127.0.0.1:{port}/api/path-builder", {
            "interests": ["Electronics", "Programming"],
            "skills": ["Python", "Arduino"],
            "education_max": "Bachelor's degree",
            "preferred_state": "Maryland",
            "salary_goal": 90000,
            "limit": 6,
        })
        bridge = post_json(f"http://127.0.0.1:{port}/api/skill-bridge", {
            "source": "Public Relations Specialists",
            "target": "Political Scientists",
        })

        stats = health.get("stats", {})
        if health.get("status") != "ok" or stats.get("occupations") != 830 or stats.get("official_sources") < 8:
            raise RuntimeError(f"Unexpected health payload: {health}")
        for marker in ["CareerProof AI", "Plan your future with AI", "Official sources only", "Real career data"]:
            if marker not in page:
                raise RuntimeError(f"Missing page marker: {marker}")
        if diagnostic.get("status") != "pass":
            raise RuntimeError(f"Live diagnostic did not pass: {diagnostic}")
        if len(universe.get("categories", [])) < 8 or not universe.get("nodes"):
            raise RuntimeError("Career Universe payload is incomplete")
        if path.get("status") != "supported" or len(path.get("results", [])) < 6:
            raise RuntimeError("Path Builder payload is incomplete")
        if bridge.get("status") != "supported" or not bridge.get("component_scores"):
            raise RuntimeError("Skill Bridge payload is incomplete")

        print(f"PASS: CareerProof honored the deployment PORT variable and launched on port {port}")
        print("PASS: health endpoint returned 830 occupations and eight source families")
        print("PASS: rendered shell contains the campaign and official-data markers")
        print("PASS: Career Universe returned eight fields and career nodes")
        print("PASS: Path Builder returned six evidence-supported matches")
        print("PASS: Skill Bridge returned its multi-signal component scores")
        print("PASS: live diagnostic returned pass")
        return 0
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
