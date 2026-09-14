"""API routes for Spy (competitor channel tracking)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

log = logging.getLogger(__name__)

from backend.services.spy import (
    MANUAL_PLATFORMS,
    add_channel,
    add_videos_by_url,
    list_channels,
    get_channel,
    delete_channel,
    sync_channel_videos,
    get_channel_videos,
)

router = APIRouter(prefix="/api/spy", tags=["spy"])


class AddChannelRequest(BaseModel):
    channel_url: str
    channel_name: str = ""


@router.post("/channels")
async def api_add_channel(req: AddChannelRequest):
    """Add a TikTok/YouTube channel to spy on."""
    result = await add_channel(req.channel_url, req.channel_name)
    if "error" in result:
        return {"status": "error", "error": result["error"]}
    return {"status": "ok", "channel": result["channel"]}


@router.get("/channels")
async def api_list_channels(status: str = "active"):
    """List all spy channels."""
    channels = await list_channels(status)
    return {"status": "ok", "channels": channels}


@router.get("/channels/{channel_id}")
async def api_get_channel(channel_id: int):
    """Get channel details."""
    channel = await get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return {"status": "ok", "channel": channel}


@router.delete("/channels/{channel_id}")
async def api_delete_channel(channel_id: int):
    """Delete a spy channel."""
    await delete_channel(channel_id)
    return {"status": "ok"}


@router.post("/channels/{channel_id}/sync")
async def api_sync_channel(channel_id: int, max_videos: int = 30):
    """Sync latest videos from a channel."""
    result = await sync_channel_videos(channel_id, max_videos)
    if "error" in result:
        return {"status": "error", "error": result["error"]}
    return {"status": "ok", **result}


class AddVideosRequest(BaseModel):
    urls: list[str] = []


@router.post("/channels/{channel_id}/videos")
async def api_add_videos(channel_id: int, req: AddVideosRequest):
    """Thêm video vào kênh bằng link — dùng cho Facebook."""
    if not req.urls:
        return {"status": "error", "error": "Chưa dán link nào"}

    result = await add_videos_by_url(channel_id, req.urls)
    if "error" in result:
        return {"status": "error", "error": result["error"]}
    return {"status": "ok", **result}


@router.get("/platforms")
async def api_platforms():
    """Cho giao diện biết nền tảng nào quét tự động, nền tảng nào phải dán link."""
    from backend.database import get_setting

    return {
        "status": "ok",
        "manual_platforms": sorted(MANUAL_PLATFORMS),
        "auto_sync": {
            "enabled": (await get_setting("spy_auto_sync_enabled", "true")).lower() == "true",
            "interval_minutes": int(await get_setting("spy_sync_interval_minutes", "180")),
            "alert_views_delta": int(await get_setting("spy_alert_views_delta", "5000")),
        },
    }


class AutoSyncSettings(BaseModel):
    enabled: bool = True
    interval_minutes: int = 180
    alert_views_delta: int = 5000


@router.put("/auto-sync")
async def api_update_auto_sync(req: AutoSyncSettings):
    """Bật/tắt và chỉnh nhịp tự động cập nhật kênh đối thủ."""
    from backend.database import set_setting
    from backend.services.scheduler import reschedule_spy_sync

    interval = max(30, min(1440, req.interval_minutes))
    await set_setting("spy_auto_sync_enabled", "true" if req.enabled else "false")
    await set_setting("spy_sync_interval_minutes", str(interval))
    await set_setting("spy_alert_views_delta", str(max(0, req.alert_views_delta)))

    reschedule_spy_sync(interval, req.enabled)

    return {
        "status": "ok",
        "auto_sync": {
            "enabled": req.enabled,
            "interval_minutes": interval,
            "alert_views_delta": max(0, req.alert_views_delta),
        },
    }


@router.post("/sync-all")
async def api_sync_all(max_videos: int = 30):
    """Sync toàn bộ kênh đang theo dõi trong một lượt."""
    channels = await list_channels("active")
    summary = []
    for ch in channels:
        result = await sync_channel_videos(ch["id"], max_videos)
        summary.append({
            "channel_id": ch["id"],
            "channel_name": ch["channel_name"],
            "new_videos": result.get("new_videos", 0),
            "updated_videos": result.get("updated_videos", 0),
            "error": result.get("error", ""),
        })
    total_new = sum(s["new_videos"] for s in summary)
    return {"status": "ok", "channels": summary, "total_new": total_new}


@router.get("/channels/{channel_id}/videos")
async def api_get_videos(
    channel_id: int,
    sort_by: str = "published_at",
    order: str = "desc",
    limit: int = 100,
    offset: int = 0,
):
    """Get videos for a channel with filtering."""
    result = await get_channel_videos(channel_id, sort_by, order, limit, offset)
    return {"status": "ok", **result}


class ReupRequest(BaseModel):
    video_url: str
    to_studio: bool = False   # tải xong đẩy thẳng vào kho Video Studio


@router.post("/reup")
async def api_reup_video(req: ReupRequest):
    """Tải video từ trang Spy về thư viện (và tuỳ chọn đưa vào Video Studio)."""
    from backend.database import get_db
    from backend.services.downloader import download_video

    try:
        video = await download_video(req.video_url)

        db = await get_db()
        await db.execute(
            "UPDATE spy_videos SET reupped = 1 WHERE video_url = ?",
            (req.video_url,),
        )
        await db.commit()

        studio_asset = None
        if req.to_studio:
            from backend.services.studio import import_from_library
            try:
                studio_asset = await import_from_library(video.filepath, video.title)
            except Exception as e:
                log.warning("Đưa video vào Studio thất bại: %s", e)

        return {
            "status": "ok",
            "message": "Đã tải video xong",
            "video": video.model_dump(),
            "studio_asset": studio_asset,
        }
    except Exception as e:
        log.error("Reup thất bại cho %s: %s", req.video_url, e)
        return {"status": "error", "error": str(e)}
