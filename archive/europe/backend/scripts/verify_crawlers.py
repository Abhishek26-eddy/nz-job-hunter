import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.crawler.ashby import AshbyCrawler
from app.crawler.greenhouse import GreenhouseCrawler
from app.crawler.lever import LeverCrawler


async def test_crawler(name, crawler, boards):
    results = []
    start = time.time()
    for board in boards:
        board_start = time.time()
        try:
            jobs = await crawler.fetch_jobs(board, company_id=0)
            results.append({
                "board": board,
                "jobs_found": len(jobs),
                "time_ms": round((time.time() - board_start) * 1000, 1),
                "first_title": jobs[0].title if jobs else None,
            })
        except Exception as exc:
            results.append({
                "board": board,
                "jobs_found": 0,
                "time_ms": round((time.time() - board_start) * 1000, 1),
                "error": str(exc),
            })
    return {
        "crawler": name,
        "boards_tested": len(boards),
        "total_jobs": sum(r["jobs_found"] for r in results),
        "time_s": round(time.time() - start, 2),
        "details": results,
    }


async def main():
    gh_boards = ["spotify", "wise", "monzo", "stripe", "deliveryhero"]
    lever_boards = ["affirm", "netlify", "robinhood", "lattice", "notion"]
    ashby_boards = ["linear", "vercel", "ramp", "figma", "supabase"]

    gh = GreenhouseCrawler()
    lev = LeverCrawler()
    ash = AshbyCrawler()

    results = await asyncio.gather(
        test_crawler("greenhouse", gh, gh_boards),
        test_crawler("lever", lev, lever_boards),
        test_crawler("ashby", ash, ashby_boards),
    )

    print(json.dumps(results, indent=2))
    total = sum(r["total_jobs"] for r in results)
    print(f"\nTotal jobs discovered across all crawlers: {total}")


if __name__ == "__main__":
    asyncio.run(main())
