from fastapi import APIRouter

router = APIRouter(prefix="/contractor")


@router.get("")
def contractor_status() -> dict[str, str]:
    return {"module": "contractor", "status": "ready"}
