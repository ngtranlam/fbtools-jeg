"""API routes for system settings and storage management."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.database import get_all_settings, set_setting
from backend.services.storage import get_storage_stats, manual_cleanup
from backend.services.telegram import test_connection as test_telegram

router = APIRouter(prefix="/api/settings", tags=["settings"])


class UpdateSettingsRequest(BaseModel):
    settings: dict[str, str]


@router.get("")
async def get_settings():
    settings = await get_all_settings()
    # Mask sensitive values
    masked = {}
    for k, v in settings.items():
        if "token" in k or "secret" in k:
            masked[k] = "***" + v[-4:] if len(v) > 4 else "***"
        else:
            masked[k] = v
    return {"status": "ok", "settings": masked}


@router.put("")
async def update_settings(req: UpdateSettingsRequest):
    for key, value in req.settings.items():
        await set_setting(key, value)
    return {"status": "ok"}


@router.get("/storage")
async def storage_stats():
    stats = await get_storage_stats()
    return {"status": "ok", **stats}


@router.post("/storage/cleanup")
async def force_cleanup():
    result = await manual_cleanup()
    return {"status": "ok", **result}


@router.post("/telegram/test")
async def telegram_test():
    result = await test_telegram()
    return result
