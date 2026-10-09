from fastapi import APIRouter

router = APIRouter(prefix="/likes")


@router.get("")
def list_likes() -> dict[str, str]:
    return {"module": "likes", "status": "ready"}
