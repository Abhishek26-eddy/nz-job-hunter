from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.application import Application, ApplicationStatus
from app.models.company import Company
from app.models.country import Country
from app.models.job import Job

router = APIRouter()


@router.get("/summary")
async def get_summary(db: AsyncSession = Depends(get_db)):
    total_jobs = (
        await db.execute(select(func.count(Job.id)).where(Job.is_active == True))
    ).scalar_one()
    total_companies = (await db.execute(select(func.count(Company.id)))).scalar_one()
    total_applications = (await db.execute(select(func.count(Application.id)))).scalar_one()

    status_counts = {
        row[0]: row[1]
        for row in (
            await db.execute(
                select(Application.status, func.count(Application.id)).group_by(Application.status)
            )
        ).all()
    }

    top_countries = [
        {"country": row[0], "jobs": row[1]}
        for row in (
            await db.execute(
                select(Country.name, func.count(Job.id))
                .join(Job, Job.country_id == Country.id)
                .where(Job.is_active == True)
                .group_by(Country.name)
                .order_by(func.count(Job.id).desc())
                .limit(10)
            )
        ).all()
    ]

    return {
        "total_jobs": total_jobs,
        "total_companies": total_companies,
        "total_applications": total_applications,
        "status_counts": status_counts,
        "top_countries": top_countries,
    }
