from fastapi import APIRouter

from backend.app.api.v1.endpoints import (
    admin,
    annotations,
    auth,
    datasets,
    health,
    jobs,
    reviews,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(annotations.router, prefix="/annotations", tags=["annotations"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(health.router, tags=["health"])
