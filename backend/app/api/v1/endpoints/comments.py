from fastapi import APIRouter

router = APIRouter(prefix="/comments")


@router.get("")
def list_comments() -> dict[str, str]:
    return {"module": "comments", "status": "ready"}
