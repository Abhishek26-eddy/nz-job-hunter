from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.job import Job
from app.schemas.common import MessageResponse
from app.services.oneclick_apply import apply_intent
from app.services.resume_service import ResumeService

router = APIRouter(tags=["one-click-apply"])


class OneClickApplyRequest(BaseModel):
    resume_id: int | None = None
    cover_letter: str = ""


@router.post("/jobs/{job_id}", response_model=MessageResponse)
async def oneclick_apply(
    job_id: int,
    resume_id: int | None = Query(None),
    cover_letter: str = Query(""),
    payload: OneClickApplyRequest | None = Body(None),
    db: AsyncSession = Depends(get_db),
):
    """Return a safe apply action for the job. Does not submit any form automatically."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if payload:
        resume_id = payload.resume_id or resume_id
        cover_letter = payload.cover_letter or cover_letter

    resume = None
    resume_service = ResumeService(db)
    if resume_id:
        resume = await resume_service.get(resume_id)
    if not resume:
        resume = await resume_service.get_master_resume()

    result = apply_intent(job, resume=resume, cover_letter=cover_letter)
    return {"message": result["message"], "data": result}
