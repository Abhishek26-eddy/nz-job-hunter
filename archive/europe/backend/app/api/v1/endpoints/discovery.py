from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.discovery import CompanyDiscoveryRequest, CompanyDiscoverySummary
from app.services.company_discovery import CompanyDiscoveryService

router = APIRouter()


@router.post("/companies", response_model=CompanyDiscoverySummary)
async def discover_companies(
    payload: CompanyDiscoveryRequest,
    db: AsyncSession = Depends(get_db),
):
    """Ingest one or more real companies discovered via ATS/career pages.

    The service auto-detects the ATS provider and board identifier from each
    career_page_url. Existing companies are updated only if the new data fills
    in missing fields or provides a more specific ATS config.
    """
    service = CompanyDiscoveryService(db)
    try:
        raw_candidates = []
        for c in payload.candidates:
            data = c.model_dump(exclude_unset=True)
            for url_field in ("career_page_url", "website", "engineering_blog_url"):
                if data.get(url_field):
                    data[url_field] = str(data[url_field])
            raw_candidates.append(data)
        result = await service.ingest(raw_candidates, source=payload.source)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Discovery ingest failed: {exc}",
        ) from exc

    return CompanyDiscoverySummary(**result)
