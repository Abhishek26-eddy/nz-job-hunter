#!/usr/bin/env python3
"""Daily Europe Job Agent runner.

Starts the local Docker stack, ensures the DB is migrated, crawls for new/updated
jobs, runs AI matching, rebuilds the dashboard, and opens it in the browser.

This is intended as a personal desktop tool — run it once or twice a day, then
let everything stop until the next run.
"""

import argparse
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_PORT = int(os.getenv("EJA_BACKEND_PORT", "8002"))
FRONTEND_PORT = int(os.getenv("EJA_FRONTEND_PORT", "3001"))
API_URL = f"http://localhost:{BACKEND_PORT}/api"
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"


def run(cmd: list[str], check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=PROJECT_ROOT, check=check, text=True, **kwargs)


def docker_compose(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return run(["docker-compose", *args], **kwargs)


def wait_for_backend(timeout: int = 120) -> bool:
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{API_URL}/v1/companies/", timeout=5) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def api_post(path: str, params: dict | None = None, json_body: dict | None = None) -> dict:
    import json
    import urllib.parse
    import urllib.request

    url = f"{API_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    body = json.dumps(json_body or {}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_get(path: str) -> dict:
    import json
    import urllib.request

    with urllib.request.urlopen(f"{API_URL}{path}", timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def open_browser() -> None:
    print(f"Opening dashboard at {FRONTEND_URL}")
    webbrowser.open(FRONTEND_URL)


def main() -> int:
    parser = argparse.ArgumentParser(description="Europe Job Agent daily runner")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser")
    parser.add_argument("--crawl-limit", type=int, default=200, help="Number of companies to crawl")
    args = parser.parse_args()

    print("=" * 60)
    print("Europe Job Agent — daily run")
    print("=" * 60)

    # 1. Start containers
    print("\n[1/8] Starting Docker containers...")
    docker_compose(["up", "-d"])

    # 2. Wait for backend to be ready
    print("\n[2/8] Waiting for backend...")
    if not wait_for_backend():
        print("Backend did not become ready", file=sys.stderr)
        return 1
    print("Backend ready")

    # 3. Run migrations
    print("\n[3/8] Running Alembic migrations...")
    docker_compose(["exec", "-T", "backend", "alembic", "upgrade", "head"])

    # 4. Seed if companies table is empty
    print("\n[4/8] Checking database seed...")
    summary = api_get("/v1/analytics/summary")
    if summary.get("total_companies", 0) == 0:
        print("Seeding companies...")
        docker_compose(["exec", "-T", "backend", "python", "scripts/seed_companies.py"])
    else:
        print(f"Already seeded with {summary['total_companies']} companies")

    # 5. Crawl for new jobs (upsert skips existing)
    print("\n[5/8] Crawling ATS providers for new jobs...")
    crawl_result = api_post("/v1/crawler/run", {"limit": args.crawl_limit})
    new_job_ids = crawl_result.get("result", {}).get("new_job_ids", [])
    print(f"Crawl result: {crawl_result.get('result', {})}")

    # 6. AI matching against master resume for new/unmatched jobs
    print("\n[6/8] Running local AI matching (embeddings + Ollama)...")
    try:
        match_result = api_post("/v1/ai/match")
        print(f"Local AI match result: {match_result}")
    except Exception as exc:
        print(f"Local AI matching failed: {exc}")

    # 7. Rebuild frontend for production and restart the dev server so it serves the updated app
    print("\n[7/8] Building frontend...")
    docker_compose(["exec", "-T", "frontend", "npm", "run", "build"])
    docker_compose(["restart", "frontend"])

    # 8. Open dashboard
    print("\n[8/8] Opening dashboard...")
    if not args.no_browser:
        open_browser()
    else:
        print(f"Dashboard ready at {FRONTEND_URL}")

    print("\nDone. Run this script again tomorrow.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
