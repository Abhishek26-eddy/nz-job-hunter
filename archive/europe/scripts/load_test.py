#!/usr/bin/env python3
"""Simple load test for the Europe Job Agent backend."""

import asyncio
import sys
import time
from statistics import mean, median, stdev

import aiohttp

URLS = [
    "http://localhost:8002/health",
    "http://localhost:8002/api/v1/companies/",
    "http://localhost:8002/api/v1/jobs/",
    "http://localhost:8002/api/v1/analytics/summary",
]

CONCURRENCY = 100
TOTAL_REQUESTS = 1000


async def fetch(session: aiohttp.ClientSession, url: str) -> tuple[float, int]:
    start = time.perf_counter()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            await resp.read()
            return time.perf_counter() - start, resp.status
    except Exception as exc:
        return time.perf_counter() - start, 0


async def worker(session: aiohttp.ClientSession, queue: asyncio.Queue, results: list):
    while True:
        try:
            url = queue.get_nowait()
        except asyncio.QueueEmpty:
            break
        results.append(await fetch(session, url))
        queue.task_done()


async def main():
    queue = asyncio.Queue()
    for i in range(TOTAL_REQUESTS):
        queue.put_nowait(URLS[i % len(URLS)])

    results: list[tuple[float, int]] = []
    start = time.perf_counter()
    async with aiohttp.ClientSession() as session:
        workers = [asyncio.create_task(worker(session, queue, results)) for _ in range(CONCURRENCY)]
        await asyncio.gather(*workers)
    duration = time.perf_counter() - start

    durations = [d for d, _ in results]
    statuses = [s for _, s in results]
    success = sum(1 for s in statuses if 200 <= s < 300)
    failed = len(results) - success

    print(f"Total requests: {len(results)}")
    print(f"Concurrency: {CONCURRENCY}")
    print(f"Duration: {duration:.2f}s")
    print(f"RPS: {len(results) / duration:.1f}")
    print(f"Success: {success} ({100 * success / len(results):.1f}%)")
    print(f"Failed: {failed}")
    if durations:
        print(f"Min: {min(durations) * 1000:.1f}ms")
        print(f"Max: {max(durations) * 1000:.1f}ms")
        print(f"Mean: {mean(durations) * 1000:.1f}ms")
        print(f"Median: {median(durations) * 1000:.1f}ms")
        print(f"P95: {sorted(durations)[int(len(durations) * 0.95)] * 1000:.1f}ms")
        if len(durations) > 1:
            print(f"StdDev: {stdev(durations) * 1000:.1f}ms")

    status_counts = {}
    for s in statuses:
        status_counts[s] = status_counts.get(s, 0) + 1
    print("Status codes:", status_counts)


if __name__ == "__main__":
    asyncio.run(main())
