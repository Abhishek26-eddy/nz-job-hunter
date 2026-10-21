import asyncio

import structlog

from app.celery_app import celery_app
from app.crawler.orchestrator import CrawlerOrchestrator
from app.notifications.slack import notify_high_match_jobs

logger = structlog.get_logger()


@celery_app.task(bind=True, max_retries=3)
def run_crawler_batch(self, limit: int = 50):
    logger.info("crawler_task_started", limit=limit)
    try:
        result = asyncio.run(_run_crawler(limit))
        # Optionally fire notifications for high-match jobs
        # asyncio.run(notify_high_match_jobs())
        return result
    except Exception as exc:
        logger.error("crawler_task_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=60)


async def _run_crawler(limit: int):
    async with CrawlerOrchestrator() as orchestrator:
        return await orchestrator.run_batch(limit=limit)
