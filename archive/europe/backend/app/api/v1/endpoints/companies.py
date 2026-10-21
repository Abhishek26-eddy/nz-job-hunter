from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.common import PaginatedResponse
from app.schemas.company import CompanyRead, CompanyUpdate
from app.services.company_service import CompanyService

router = APIRouter()


@router.get("", response_model=PaginatedResponse[CompanyRead])
@router.get("/", response_model=PaginatedResponse[CompanyRead])
async def list_companies(
    country_id: int | None = None,
    industry: str | None = None,
    visa_sponsorship: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = CompanyService(db)
    items, total = await service.list_all(
        country_id=country_id,
        industry=industry,
        visa_sponsorship=visa_sponsorship,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return PaginatedResponse[CompanyRead].create(
        items=items, total=total, page=page, page_size=page_size
    )


@router.get("/{company_id}", response_model=CompanyRead)
async def get_company(company_id: int, db: AsyncSession = Depends(get_db)):
    service = CompanyService(db)
    company = await service.get(company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


@router.patch("/{company_id}", response_model=CompanyRead)
async def update_company(
    company_id: int,
    payload: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = CompanyService(db)
    company = await service.update(company_id, payload)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company
