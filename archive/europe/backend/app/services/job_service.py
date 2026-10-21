from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.application import Application
from app.models.company import Company
from app.models.country import Country
from app.models.job import Job
from app.schemas.job import JobFilter


def _attach_application_status(jobs: list[Job]) -> None:
    for job in jobs:
        applications = job.applications or []
        latest = max(applications, key=lambda a: a.created_at, default=None)
        job.application_status = latest.status if latest else None


class JobService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, job_id: int) -> Job | None:
        job = (
            await self.db.execute(
                select(Job)
                .options(joinedload(Job.company), joinedload(Job.country))
                .where(Job.id == job_id)
            )
        ).unique().scalar_one_or_none()
        if job:
            _attach_application_status([job])
        return job

    async def list_jobs(
        self,
        filters: JobFilter,
        limit: int = 20,
        offset: int = 0,
        order_by: str = "match_score",
    ) -> tuple[list[Job], int]:
        query = (
            select(Job)
            .options(joinedload(Job.company), joinedload(Job.country))
            .where(Job.is_active == True)
            .where(Job.is_deleted == False)
        )

        if not filters.include_rejected:
            query = query.where(Job.rejected == False)

        if filters.role_priority:
            query = query.where(Job.role_priority == filters.role_priority)

        if filters.search:
            term = f"%{filters.search}%"
            query = query.where(
                or_(
                    Job.title.ilike(term),
                    Job.description.ilike(term),
                    Company.name.ilike(term),
                )
            ).join(Job.company)
        else:
            query = query.join(Job.company, isouter=True)

        if filters.country_id:
            query = query.where(Job.country_id == filters.country_id)
        if filters.country_code:
            query = query.join(Job.country).where(Country.code == filters.country_code)
        if filters.workplace_type:
            query = query.where(Job.workplace_type == filters.workplace_type)
        if filters.min_match_score is not None:
            query = query.where(Job.match_score >= filters.min_match_score)
        if filters.should_apply is not None:
            query = query.where(Job.should_apply == filters.should_apply)
        if filters.visa_sponsorship_inferred:
            query = query.where(Job.visa_sponsorship_inferred == filters.visa_sponsorship_inferred)
        if filters.remote:
            query = query.where(
                or_(Job.workplace_type == "remote", Job.workplace_type == "hybrid")
            )
        if filters.min_salary is not None:
            query = query.where(
                or_(Job.salary_max >= filters.min_salary, Job.salary_estimate != "")
            )
        if filters.max_salary is not None:
            query = query.where(Job.salary_min <= filters.max_salary)
        if filters.company_size:
            query = query.where(Company.size == filters.company_size)
        if filters.skills:
            for skill in filters.skills:
                query = query.where(Job.description.ilike(f"%{skill}%"))

        total = (await self.db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()  # type: ignore

        order_column = getattr(Job, order_by, Job.created_at)
        if order_by == "match_score":
            order_column = Job.match_score.desc().nullslast()  # type: ignore
        else:
            order_column = order_column.desc()  # type: ignore

        items = (
            (await self.db.execute(query.order_by(order_column).limit(limit).offset(offset)))  # type: ignore
            .scalars()
            .all()
        )
        items = list(items)
        _attach_application_status(items)
        return items, total

    async def update_match(self, job_id: int, data: dict) -> Job | None:
        job = await self.get(job_id)
        if not job:
            return None
        for key, value in data.items():
            setattr(job, key, value)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def get_high_match_jobs(
        self, min_score: float = 85, limit: int = 50
    ) -> list[Job]:
        query = (
            select(Job)
            .options(joinedload(Job.company), joinedload(Job.country))
            .where(Job.is_active == True)
            .where(Job.is_deleted == False)
            .where(Job.match_score >= min_score)
            .order_by(Job.match_score.desc())  # type: ignore
            .limit(limit)
        )
        items = list((await self.db.execute(query)).unique().scalars().all())
        _attach_application_status(items)
        return items
