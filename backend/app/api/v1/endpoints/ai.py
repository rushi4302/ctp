from fastapi import APIRouter

router = APIRouter(prefix="/ai")


@router.get("")
def ai_status() -> dict[str, str]:
    return {"module": "ai", "status": "ready"}
