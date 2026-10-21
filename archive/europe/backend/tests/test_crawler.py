import pytest

from app.crawler.base import BaseJobCrawler


class DummyCrawler(BaseJobCrawler):
    platform = "dummy"

    async def fetch_jobs(self, company_identifier, company_id):
        return []


@pytest.mark.asyncio
async def test_is_target_role():
    crawler = DummyCrawler()
    assert crawler.is_target_role("Senior DevOps Engineer") is True
    assert crawler.is_target_role("Frontend Developer") is False
    assert crawler.is_target_role("Backend Engineer") is False
    assert crawler.is_target_role("Platform Engineer") is True
