from fastapi import APIRouter

router = APIRouter(prefix="/users")


@router.get("")
def list_users() -> dict[str, str]:
    return {"module": "users", "status": "ready"}
