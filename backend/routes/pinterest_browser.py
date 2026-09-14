"""API routes for Pinterest Browser automation (Camoufox-based)."""

from __future__ import annotations

import json
import logging
import traceback

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database import get_db

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/pinterest-browser", tags=["pinterest-browser"])


class PinterestLoginRequest(BaseModel):
    account_name: str


class PinterestPublishRequest(BaseModel):
    channel_id: int
    filepath: str
    title: str
    description: str = ""
    board_name: str = ""
    link: str = ""  # Store / product URL


@router.post("/login")
async def pinterest_login(req: PinterestLoginRequest):
    """Open Camoufox browser for user to login to Pinterest manually."""
    try:
        from backend.services.pinterest_browser import login_pinterest
        result = await login_pinterest(req.account_name)

        if result["success"]:
            # Update channel in DB if exists
            db = await get_db()
            await db.execute(
                "UPDATE channels SET status = 'active', updated_at = datetime('now') "
                "WHERE platform = 'pinterest' AND channel_name = ?",
                (req.account_name,),
            )
            await db.commit()

        return {"status": "ok", **result}
    except Exception as e:
        log.error(f"Pinterest login error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login/{channel_id}")
async def pinterest_login_by_id(channel_id: int):
    """Login for a specific Pinterest channel by ID."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT channel_name FROM channels WHERE id = ? AND platform = 'pinterest'",
        (channel_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Pinterest channel not found")

    account_name = row["channel_name"]
    try:
        from backend.services.pinterest_browser import login_pinterest
        result = await login_pinterest(account_name)

        if result["success"]:
            await db.execute(
                "UPDATE channels SET status = 'active', updated_at = datetime('now') WHERE id = ?",
                (channel_id,),
            )
            await db.commit()

        return {"status": "ok", **result}
    except Exception as e:
        log.error(f"Pinterest login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/boards/{channel_id}")
async def get_boards(channel_id: int):
    """Get boards for a Pinterest channel via browser."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT channel_name FROM channels WHERE id = ? AND platform = 'pinterest'",
        (channel_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Pinterest channel not found")

    try:
        from backend.services.pinterest_browser import get_boards_browser
        boards = await get_boards_browser(row["channel_name"])
        return {"status": "ok", "boards": boards}
    except Exception as e:
        log.error(f"Get boards error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate/{channel_id}")
async def validate_session(channel_id: int):
    """Check if Pinterest browser session is still valid."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT channel_name FROM channels WHERE id = ? AND platform = 'pinterest'",
        (channel_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Pinterest channel not found")

    try:
        from backend.services.pinterest_browser import validate_session as _validate
        result = await _validate(row["channel_name"])

        # Update channel status based on validation
        new_status = "active" if result.get("valid") else "error"
        await db.execute(
            "UPDATE channels SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (new_status, channel_id),
        )
        await db.commit()

        return {"status": "ok", **result}
    except Exception as e:
        return {"status": "ok", "valid": False, "error": str(e)}


@router.post("/publish")
async def publish_pin(req: PinterestPublishRequest):
    """Publish a video pin via browser automation."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT channel_name FROM channels WHERE id = ? AND platform = 'pinterest'",
        (req.channel_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Pinterest channel not found")

    try:
        from backend.services.pinterest_browser import publish_video_pin_browser
        result = await publish_video_pin_browser(
            account_name=row["channel_name"],
            filepath=req.filepath,
            title=req.title,
            description=req.description,
            board_name=req.board_name,
            link=req.link,
        )
        return {"status": "ok", **result}
    except Exception as e:
        log.error(f"Pinterest publish error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{channel_id}")
async def delete_session(channel_id: int):
    """Delete saved Pinterest session cookies."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT channel_name FROM channels WHERE id = ? AND platform = 'pinterest'",
        (channel_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Pinterest channel not found")

    try:
        from backend.services.pinterest_browser import delete_session as _delete
        deleted = await _delete(row["channel_name"])
        if deleted:
            await db.execute(
                "UPDATE channels SET status = 'inactive', updated_at = datetime('now') WHERE id = ?",
                (channel_id,),
            )
            await db.commit()
        return {"status": "ok", "deleted": deleted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
