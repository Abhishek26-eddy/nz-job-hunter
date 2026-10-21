from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.application import ApplicationCreate, ApplicationRead, ApplicationStatusUpdate
from app.schemas.common import PaginatedResponse
from app.services.application_service import ApplicationService

router = APIRouter()


@router.get("", response_model=PaginatedResponse[ApplicationRead])
@router.get("/", response_model=PaginatedResponse[ApplicationRead])
async def list_applications(
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = ApplicationService(db)
    items, total = await service.list_by_user(
        user_id=1,  # placeholder until auth is added
        status=status,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return PaginatedResponse[ApplicationRead].create(
        items=items, total=total, page=page, page_size=page_size
    )


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def create_application(
    payload: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
):
    service = ApplicationService(db)
    return await service.create(user_id=1, obj=payload)


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application(application_id: int, db: AsyncSession = Depends(get_db)):
    service = ApplicationService(db)
    application = await service.get(application_id)
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
        )
    return application


@router.patch("/{application_id}/status", response_model=ApplicationRead)
async def update_application_status(
    application_id: int,
    payload: ApplicationStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = ApplicationService(db)
    application = await service.update_status(application_id, payload)
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
        )
    return application
