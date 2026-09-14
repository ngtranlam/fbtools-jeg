from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.models import MetadataUpdateRequest
from backend.services.downloader import get_video
from backend.services.metadata import read_metadata, write_metadata, strip_metadata

router = APIRouter(prefix="/api/metadata", tags=["metadata"])


@router.get("/{video_id}")
async def api_get_metadata(video_id: str):
    video = get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    meta = await read_metadata(video.filepath)
    return {"metadata": meta.model_dump()}


@router.put("/{video_id}")
async def api_update_metadata(video_id: str, req: MetadataUpdateRequest):
    video = get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    ok = await write_metadata(video.filepath, req.metadata)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to update metadata")
    return {"success": True}


@router.post("/strip/{video_id}")
async def api_strip_metadata(video_id: str):
    video = get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    ok = await strip_metadata(video.filepath)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to strip metadata")
    return {"success": True}
