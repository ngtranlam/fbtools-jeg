"""API routes for managing multi-platform channels (Pinterest, YouTube)."""

from __future__ import annotations

import json
import logging
import traceback

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database import get_db

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/channels", tags=["channels"])


class ChannelCreate(BaseModel):
    platform: str  # 'pinterest' | 'youtube'
    channel_name: str
    channel_id: str = ""
    avatar_url: str = ""
    credentials: dict = {}  # {access_token, refresh_token, client_id, client_secret}
    extra_data: dict = {}   # {board_id, playlist_id, ...}


class ChannelUpdate(BaseModel):
    channel_name: str | None = None
    avatar_url: str | None = None
    credentials: dict | None = None
    extra_data: dict | None = None
    status: str | None = None


@router.get("")
async def list_channels(platform: str | None = None, status: str = "active"):
    """List all channels, optionally filtered by platform."""
    db = await get_db()
    query = "SELECT * FROM channels WHERE status = ?"
    params: list = [status]

    if platform:
        query += " AND platform = ?"
        params.append(platform)

    query += " ORDER BY created_at DESC"
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    channels = []
    for row in rows:
        channels.append({
            "id": row["id"],
            "platform": row["platform"],
            "channel_name": row["channel_name"],
            "channel_id": row["channel_id"],
            "avatar_url": row["avatar_url"],
            "followers_count": row["followers_count"],
            "status": row["status"],
            "has_credentials": bool(row["credentials"] and row["credentials"] != "{}"),
            "extra_data": json.loads(row["extra_data"]) if row["extra_data"] else {},
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        })

    return {"status": "ok", "channels": channels, "total": len(channels)}


@router.post("")
async def create_channel(req: ChannelCreate):
    """Add a new Pinterest or YouTube channel."""
    if req.platform not in ("pinterest", "youtube"):
        raise HTTPException(status_code=400, detail="Platform must be 'pinterest' or 'youtube'")

    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO channels (platform, channel_name, channel_id, avatar_url, credentials, extra_data)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                req.platform,
                req.channel_name,
                req.channel_id,
                req.avatar_url,
                json.dumps(req.credentials),
                json.dumps(req.extra_data),
            ),
        )
        await db.commit()

        cursor = await db.execute("SELECT last_insert_rowid()")
        row = await cursor.fetchone()
        new_id = row[0] if row else 0

        log.info(f"Channel created: {req.platform}/{req.channel_name} (ID: {new_id})")
        return {"status": "ok", "channel_id": new_id}

    except Exception as e:
        log.error(f"Failed to create channel: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{channel_id}")
async def update_channel(channel_id: int, req: ChannelUpdate):
    """Update a channel's details."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM channels WHERE id = ?", (channel_id,))
    existing = await cursor.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Channel not found")

    updates = []
    params = []
    if req.channel_name is not None:
        updates.append("channel_name = ?")
        params.append(req.channel_name)
    if req.avatar_url is not None:
        updates.append("avatar_url = ?")
        params.append(req.avatar_url)
    if req.credentials is not None:
        updates.append("credentials = ?")
        params.append(json.dumps(req.credentials))
    if req.extra_data is not None:
        updates.append("extra_data = ?")
        params.append(json.dumps(req.extra_data))
    if req.status is not None:
        updates.append("status = ?")
        params.append(req.status)

    if updates:
        updates.append("updated_at = datetime('now')")
        params.append(channel_id)
        await db.execute(
            f"UPDATE channels SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        await db.commit()

    return {"status": "ok"}


@router.delete("/{channel_id}")
async def delete_channel(channel_id: int):
    """Remove a channel."""
    db = await get_db()
    cursor = await db.execute("SELECT id FROM channels WHERE id = ?", (channel_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Channel not found")

    await db.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
    await db.commit()
    return {"status": "ok"}


@router.post("/{channel_id}/validate")
async def validate_channel(channel_id: int):
    """Test channel credentials."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT platform FROM channels WHERE id = ?", (channel_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Channel not found")

    platform = row["platform"]
    try:
        if platform == "pinterest":
            from backend.services.pinterest import validate_credentials
            result = await validate_credentials(channel_id)
        elif platform == "youtube":
            from backend.services.youtube import validate_credentials
            result = await validate_credentials(channel_id)
        else:
            result = {"valid": False, "error": f"Unknown platform: {platform}"}

        return {"status": "ok", **result}
    except Exception as e:
        return {"status": "ok", "valid": False, "error": str(e)}


@router.get("/{channel_id}/boards")
async def list_boards(channel_id: int):
    """Pinterest: list boards for a channel."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT platform FROM channels WHERE id = ?", (channel_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Channel not found")
    if row["platform"] != "pinterest":
        raise HTTPException(status_code=400, detail="Boards are only available for Pinterest channels")

    try:
        from backend.services.pinterest import get_boards
        boards = await get_boards(channel_id)
        return {"status": "ok", "boards": boards}
    except Exception as e:
        log.error(f"Failed to list boards: {e}")
        raise HTTPException(status_code=500, detail=str(e))
