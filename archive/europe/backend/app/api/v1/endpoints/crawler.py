from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawler.orchestrator import CrawlerOrchestrator
from app.db.session import get_db

router = APIRouter()


@router.post("/run")
async def run_crawler(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    orchestrator = CrawlerOrchestrator(db=db)
    result = await orchestrator.run_batch(limit=limit)
    return {"status": "ok", "result": result}
