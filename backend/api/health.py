from fastapi import APIRouter
from config import settings

router = APIRouter()


@router.get("")
async def health():
    return {
        "status": "ok",
        "provider": settings.ai_provider,
        "model": settings.active_model,
    }
