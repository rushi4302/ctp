from fastapi import APIRouter

router = APIRouter(prefix="/posts")


@router.get("")
def list_posts() -> dict[str, str]:
    return {"module": "posts", "status": "ready"}
