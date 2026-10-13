from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/contractor")


@router.get("")
def contractor_status() -> dict[str, str]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Use /api/v1/field-worker/issues for assigned contractor work.",
    )
