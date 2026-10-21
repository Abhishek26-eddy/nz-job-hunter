import io
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume import Resume
from app.models.user import User
from app.schemas.resume import ResumeCreate


class ResumeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, resume_id: int) -> Resume | None:
        return (
            await self.db.execute(select(Resume).where(Resume.id == resume_id))
        ).scalar_one_or_none()

    async def get_master_resume(self) -> Resume | None:
        return (
            await self.db.execute(
                select(Resume).where(Resume.is_master == True).limit(1)
            )
        ).scalar_one_or_none()

    async def list_by_user(self, user_id: int, limit: int = 50) -> list[Resume]:
        return list(
            (
                await self.db.execute(
                    select(Resume).where(Resume.user_id == user_id).limit(limit)
                )
            )
            .scalars()
            .all()
        )

    async def create(self, obj: ResumeCreate) -> Resume:
        resume = Resume(**obj.model_dump(exclude_unset=True))
        self.db.add(resume)
        await self.db.commit()
        await self.db.refresh(resume)
        return resume

    async def ensure_default_user(self) -> User:
        user = (
            await self.db.execute(select(User).where(User.id == 1))
        ).scalar_one_or_none()
        if not user:
            user = User(
                id=1,
                email="user@example.com",
                full_name="Default User",
                is_active=True,
            )
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
        return user
