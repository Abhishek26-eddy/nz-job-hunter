from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.cover_letter import CoverLetterGenerator
from app.ai.resume_tailor import ResumeTailor
from app.db.session import get_db
from app.services.job_service import JobService
from app.services.matching_service import LocalMatchingService
from app.services.resume_service import ResumeService

router = APIRouter()


class MatchBatchRequest(BaseModel):
    job_ids: list[int] | None = None
    top_n: int | None = None


@router.post("/match/{job_id}")
async def ai_match_job(job_id: int, db: AsyncSession = Depends(get_db)):
    job_service = JobService(db)
    job = await job_service.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    master = await ResumeService(db).get_master_resume()
    if not master:
        raise HTTPException(status_code=400, detail="Upload a master resume first")

    service = LocalMatchingService(db)
    try:
        return await service.match_single(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/match")
async def ai_match_batch(
    payload: MatchBatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run the local embedding + Ollama pipeline for the given jobs (or all jobs).

    This endpoint is intended for the daily workflow.
    """
    service = LocalMatchingService(db)
    return await service.run(payload.job_ids, payload.top_n)


@router.post("/tailor-resume/{job_id}")
async def ai_tailor_resume(
    job_id: int,
    resume_id: int,
    db: AsyncSession = Depends(get_db),
):
    job_service = JobService(db)
    resume_service = ResumeService(db)
    job = await job_service.get(job_id)
    resume = await resume_service.get(resume_id)
    if not job or not resume:
        raise HTTPException(status_code=404, detail="Job or resume not found")

    tailor = ResumeTailor()
    return await tailor.tailor(
        master_resume_text=resume.content_text or "",
        job_title=job.title,
        job_description=job.description or "",
        company_name=job.company.name if job.company else None,
    )


@router.post("/cover-letter/{job_id}")
async def ai_cover_letter(
    job_id: int,
    resume_id: int,
    db: AsyncSession = Depends(get_db),
):
    job_service = JobService(db)
    resume_service = ResumeService(db)
    job = await job_service.get(job_id)
    resume = await resume_service.get(resume_id)
    if not job or not resume:
        raise HTTPException(status_code=404, detail="Job or resume not found")

    generator = CoverLetterGenerator()
    return await generator.generate(
        resume_text=resume.content_text or "",
        job_title=job.title,
        job_description=job.description or "",
        company_name=job.company.name if job.company else None,
    )
