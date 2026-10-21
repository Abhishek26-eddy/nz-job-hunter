import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.resume_tailor import ResumeTailor
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.resume import ResumeCreate, ResumeRead
from app.services.job_service import JobService
from app.services.resume_service import ResumeService

router = APIRouter()


def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    text_parts = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)


@router.get("", response_model=list[ResumeRead])
@router.get("/", response_model=list[ResumeRead])
async def list_resumes(db: AsyncSession = Depends(get_db)):
    service = ResumeService(db)
    return await service.list_by_user(user_id=1)


@router.post("/upload", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    is_master: bool = False,
    db: AsyncSession = Depends(get_db),
):
    service = ResumeService(db)
    await service.ensure_default_user()

    content = await file.read()
    text = ""
    if file.filename and file.filename.lower().endswith(".pdf"):
        text = extract_text_from_pdf(content)

    if is_master:
        existing = await service.get_master_resume()
        if existing:
            existing.content_text = text
            existing.file_name = file.filename
            await db.commit()
            await db.refresh(existing)
            return existing

    resume = await service.create(
        ResumeCreate(
            user_id=1,
            name=file.filename or "Untitled",
            is_master=is_master,
            content_text=text,
            file_name=file.filename,
        )
    )
    return resume


@router.post("/{job_id}/tailor")
async def tailor_resume_for_job(
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

    tailor = ResumeTailor()
    result = await tailor.tailor(
        master_resume_text=resume.content_text or "",
        job_title=job.title,
        job_description=job.description or "",
        company_name=job.company.name if job.company else None,
    )
    return result
