import httpx
import structlog

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.services.job_service import JobService

logger = structlog.get_logger()
settings = get_settings()


class SlackNotifier:
    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or settings.slack_webhook_url

    async def send(self, text: str, blocks: list[dict] | None = None) -> bool:
        if not self.webhook_url:
            logger.info("slack_no_webhook", message=text)
            return False
        payload = {"text": text}
        if blocks:
            payload["blocks"] = blocks
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.webhook_url, json=payload)
                response.raise_for_status()
            return True
        except Exception as exc:
            logger.error("slack_send_failed", error=str(exc))
            return False


async def notify_high_match_jobs(min_score: float = 85, limit: int = 5):
    if not settings.slack_webhook_url:
        return

    async with AsyncSessionLocal() as db:
        service = JobService(db)
        jobs = await service.get_high_match_jobs(min_score=min_score, limit=limit)
        if not jobs:
            return

        notifier = SlackNotifier()
        for job in jobs:
            text = (
                f"🔥 {job.match_score or 0}% Match: {job.title} at "
                f"{job.company.name if job.company else 'Unknown'} - {job.location or 'Remote'} "
                f"(Visa: {job.visa_sponsorship_inferred})"
            )
            await notifier.send(text)
