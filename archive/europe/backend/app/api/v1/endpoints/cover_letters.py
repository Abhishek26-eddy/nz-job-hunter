from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.cover_letter import CoverLetterGenerator
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.cover_letter import CoverLetterCreate, CoverLetterRead
from app.services.job_service import JobService
from app.services.resume_service import ResumeService

router = APIRouter()


@router.post("/generate/{job_id}", response_model=CoverLetterRead, status_code=status.HTTP_201_CREATED)
async def generate_cover_letter(
    job_id: int,
    resume_id: int,
    db: AsyncSession = Depends(get_db),
):
    resume_service = ResumeService(db)
    job_service = JobService(db)

    resume = await resume_service.get(resume_id)
    job = await job_service.get(job_id)
    if not resume or not job:
        raise HTTPException(status_code=404, detail="Resume or job not found")

    generator = CoverLetterGenerator()
    result = await generator.generate(
        resume_text=resume.content_text or "",
        job_title=job.title,
        job_description=job.description or "",
        company_name=job.company.name if job.company else None,
    )

    cover_letter = CoverLetterCreate(
        user_id=1,
        job_id=job_id,
        title=f"Cover Letter - {job.title}",
        content=result["content"],
        word_count=result["word_count"],
    )
    # Save to DB (requires a service method or direct creation)
    from app.models.cover_letter import CoverLetter

    cover = CoverLetter(**cover_letter.model_dump())
    db.add(cover)
    await db.commit()
    await db.refresh(cover)
    return cover
