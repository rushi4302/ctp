from fastapi import APIRouter

from app.api.v1.endpoints import (
    ai,
    auth,
    civic_issues,
    comments,
    contractor,
    field_worker,
    likes,
    municipality,
    posts,
    reports,
    search,
    transparency,
    users,
)

router = APIRouter()

router.include_router(auth.router, tags=["auth"])
router.include_router(users.router, tags=["users"])
router.include_router(reports.router, tags=["reports"])
router.include_router(civic_issues.router, tags=["civic-issues"])
router.include_router(field_worker.router, tags=["field-worker"])
router.include_router(transparency.router, tags=["transparency"])
router.include_router(posts.router, tags=["posts"])
router.include_router(comments.router, tags=["comments"])
router.include_router(likes.router, tags=["likes"])
router.include_router(search.router, tags=["search"])
router.include_router(municipality.router, tags=["municipality"])
router.include_router(contractor.router, tags=["contractor"])
router.include_router(ai.router, tags=["ai"])