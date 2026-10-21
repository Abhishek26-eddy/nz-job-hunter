from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate


class CompanyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, company_id: int) -> Company | None:
        return (
            await self.db.execute(
                select(Company).options(joinedload(Company.country)).where(Company.id == company_id)
            )
        ).unique().scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Company | None:
        return (
            await self.db.execute(
                select(Company).options(joinedload(Company.country)).where(Company.slug == slug)
            )
        ).unique().scalar_one_or_none()

    async def list_all(
        self,
        country_id: int | None = None,
        industry: str | None = None,
        visa_sponsorship: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Company], int]:
        query = select(Company).options(joinedload(Company.country)).where(Company.is_active == True)
        if country_id:
            query = query.where(Company.country_id == country_id)
        if industry:
            query = query.where(Company.industry.ilike(f"%{industry}%"))
        if visa_sponsorship:
            query = query.where(Company.visa_sponsorship == visa_sponsorship)

        total = (
            await self.db.execute(
                select(func.count()).select_from(query.subquery())  # type: ignore
            )
        ).scalar_one()
        items = (
            (
                await self.db.execute(
                    query.order_by(Company.name).limit(limit).offset(offset)
                )
            )
            .unique()
            .scalars()
            .all()
        )
        return list(items), total

    async def create(self, obj: CompanyCreate) -> Company:
        company = Company(**obj.model_dump(exclude_unset=True))
        self.db.add(company)
        await self.db.commit()
        await self.db.refresh(company)
        return company

    async def update(self, company_id: int, obj: CompanyUpdate) -> Company | None:
        company = await self.get(company_id)
        if not company:
            return None
        for field, value in obj.model_dump(exclude_unset=True).items():
            setattr(company, field, value)
        await self.db.commit()
        await self.db.refresh(company, attribute_names=["country"])
        return company
