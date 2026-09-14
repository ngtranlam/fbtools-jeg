from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.services.checker import check_uniqueness, check_variants_for_job

router = APIRouter(prefix="/api/check", tags=["check"])


@router.post("/")
async def api_check(data: dict):
    video_paths = data.get("video_paths", [])
    if not video_paths:
        raise HTTPException(status_code=400, detail="No video paths provided")
    report = await check_uniqueness(video_paths)
    return {"success": True, "report": report.model_dump()}


@router.get("/job/{job_id}")
async def api_check_job(job_id: str):
    try:
        report = await check_variants_for_job(job_id)
        return {"success": True, "report": report.model_dump()}
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e))
