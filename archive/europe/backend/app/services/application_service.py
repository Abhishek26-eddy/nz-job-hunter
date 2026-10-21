from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.application import Application, ApplicationStatus
from app.models.company import Company
from app.models.job import Job
from app.schemas.application import ApplicationCreate, ApplicationStatusUpdate


class ApplicationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, application_id: int) -> Application | None:
        return (
            await self.db.execute(
                select(Application)
                .options(
                    joinedload(Application.job).joinedload(Job.company).joinedload(Company.country),
                    joinedload(Application.job).joinedload(Job.country),
                )
                .where(Application.id == application_id)
            )
        ).unique().scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: int,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Application], int]:
        query = (
            select(Application)
            .options(
                joinedload(Application.job).joinedload(Job.company).joinedload(Company.country),
                joinedload(Application.job).joinedload(Job.country),
            )
            .where(Application.user_id == user_id)
        )
        if status:
            query = query.where(Application.status == status)

        total = (await self.db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()  # type: ignore
        items = (
            (await self.db.execute(
                query.order_by(Application.created_at.desc()).limit(limit).offset(offset)
            ))
            .scalars()
            .all()
        )
        return list(items), total

    async def create(self, user_id: int, obj: ApplicationCreate) -> Application:
        # Upsert: a job should only ever have one application record per user.
        existing = (
            await self.db.execute(
                select(Application).where(
                    Application.job_id == obj.job_id,
                    Application.user_id == user_id,
                )
            )
        ).scalar_one_or_none()

        if existing:
            for key, value in obj.model_dump(exclude_unset=True, exclude={"job_id"}).items():
                setattr(existing, key, value)
            if existing.status == ApplicationStatus.APPLIED and not existing.applied_at:
                existing.applied_at = datetime.utcnow()
            existing.updated_at = datetime.utcnow()
            await self.db.commit()
            return await self.get(existing.id)

        application = Application(user_id=user_id, **obj.model_dump(exclude_unset=True))
        if application.status == ApplicationStatus.APPLIED:
            application.applied_at = datetime.utcnow()
        self.db.add(application)
        await self.db.commit()
        return await self.get(application.id)

    async def update_status(
        self, application_id: int, obj: ApplicationStatusUpdate
    ) -> Application | None:
        application = await self.get(application_id)
        if not application:
            return None
        application.status = obj.status
        if obj.notes:
            application.notes = obj.notes
        if obj.status == ApplicationStatus.APPLIED and not application.applied_at:
            application.applied_at = datetime.utcnow()
        application.updated_at = datetime.utcnow()
        await self.db.commit()
        return await self.get(application.id)

    async def get_counts_by_status(self, user_id: int) -> dict[str, int]:
        query = (
            select(Application.status, func.count(Application.id))
            .group_by(Application.status)
        )
        rows = (await self.db.execute(query)).all()
        return {row[0]: row[1] for row in rows}
