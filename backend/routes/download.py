from __future__ import annotations

import logging
import traceback
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File

from backend.config import TEMP_DIR, DOWNLOADS_DIR
from backend.models import DownloadRequest, VideoInfo
from backend.services.downloader import (
    download_video, get_all_videos, get_video, delete_video, add_uploaded_video,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.post("/download")
async def api_download(req: DownloadRequest):
    try:
        logger.info(f"Download request: {req.url}")
        video = await download_video(req.url)
        logger.info(f"Download complete: {video.title}")
        return {"success": True, "video": video.model_dump()}
    except Exception as e:
        logger.error(f"Download error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upload")
async def api_upload(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    logger.info(f"Upload request: {file.filename} ({file.size} bytes)")
    temp_path = TEMP_DIR / file.filename
    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)
        logger.info(f"File saved to temp: {temp_path}")
    except Exception as e:
        logger.error(f"Upload save error: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to save file: {e}")

    try:
        video = await add_uploaded_video(temp_path, file.filename)
        logger.info(f"Upload complete: {video.title}")
        return {"success": True, "video": video.model_dump()}
    except Exception as e:
        logger.error(f"Upload process error: {e}\n{traceback.format_exc()}")
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
async def api_list_videos():
    videos = get_all_videos()
    return {"videos": [v.model_dump() for v in videos]}


@router.get("/{video_id}")
async def api_get_video(video_id: str):
    video = get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return {"video": video.model_dump()}


@router.delete("/{video_id}")
async def api_delete_video(video_id: str):
    ok = delete_video(video_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Video not found")
    return {"success": True}
