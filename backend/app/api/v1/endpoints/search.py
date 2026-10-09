from fastapi import APIRouter

router = APIRouter(prefix="/search")


@router.get("")
def search_status() -> dict[str, str]:
    return {"module": "search", "status": "ready"}
