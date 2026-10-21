from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.matching_service import LocalMatchingService
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.common import PaginatedResponse
from app.schemas.job import JobFilter, JobRead, JobUpdate
from app.services.job_service import JobService
from app.services.resume_service import ResumeService

router = APIRouter()


@router.get("", response_model=PaginatedResponse[JobRead])
@router.get("/", response_model=PaginatedResponse[JobRead])
async def list_jobs(
    search: str | None = None,
    country_code: str | None = None,
    workplace_type: str | None = None,
    min_match_score: float | None = Query(None, ge=0, le=100),
    should_apply: bool | None = Query(None),
    visa_sponsorship_inferred: str | None = None,
    remote: bool | None = None,
    company_size: str | None = None,
    role_priority: str | None = None,
    include_rejected: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    order_by: str = Query("match_score"),
    db: AsyncSession = Depends(get_db),
):
    filters = JobFilter(
        search=search,
        country_code=country_code,
        workplace_type=workplace_type,
        min_match_score=min_match_score,
        should_apply=should_apply,
        visa_sponsorship_inferred=visa_sponsorship_inferred,
        remote=remote,
        company_size=company_size,
        role_priority=role_priority,
        include_rejected=include_rejected,
    )
    service = JobService(db)
    items, total = await service.list_jobs(
        filters=filters,
        limit=page_size,
        offset=(page - 1) * page_size,
        order_by=order_by,
    )
    return PaginatedResponse[JobRead].create(
        items=items, total=total, page=page, page_size=page_size
    )


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    service = JobService(db)
    job = await service.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.post("/{job_id}/match")
async def match_job(job_id: int, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    job_service = JobService(db)
    resume_service = ResumeService(db)
    job = await job_service.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    master_resume = await resume_service.get_master_resume()
    if not master_resume:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a master resume first",
        )

    service = LocalMatchingService(db)
    try:
        result = await service.match_single(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    await job_service.update_match(job_id, {
        "match_score": result["score"],
        "match_reason": result["reason"],
        "strengths": result["strengths"],
        "missing_skills": result["missing_skills"],
        "salary_estimate": result["salary_estimate"],
        "visa_sponsorship_inferred": result["visa_probability"],
        "should_apply": result["should_apply"],
        "confidence": result["confidence"],
    })
    return result
