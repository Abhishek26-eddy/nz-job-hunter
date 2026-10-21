from fastapi import APIRouter

from app.api.v1.endpoints import (
    ai,
    analytics,
    applications,
    companies,
    cover_letters,
    crawler,
    discovery,
    jobs,
    oneclick_apply,
    resumes,
)

api_router = APIRouter(prefix="/v1")

api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(cover_letters.router, prefix="/cover-letters", tags=["cover-letters"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(crawler.router, prefix="/crawler", tags=["crawler"])
api_router.include_router(discovery.router, prefix="/discovery", tags=["discovery"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(oneclick_apply.router, prefix="/apply", tags=["one-click-apply"])
