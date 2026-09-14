"""API routes for AI caption rewriting."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.ai_caption import rewrite_caption, rewrite_caption_batch, spin_captions

router = APIRouter(prefix="/api/ai", tags=["ai"])


class RewriteCaptionRequest(BaseModel):
    original_caption: str = ""
    page_name: str = ""
    page_category: str = ""
    video_title: str = ""
    language: str = "en"


class RewriteBatchRequest(BaseModel):
    original_caption: str = ""
    page_ids: list[int] = []
    language: str = "en"


@router.post("/rewrite-caption")
async def api_rewrite_caption(req: RewriteCaptionRequest):
    """Rewrite a single caption for a specific page."""
    result = await rewrite_caption(
        original_caption=req.original_caption,
        page_name=req.page_name,
        page_category=req.page_category,
        video_title=req.video_title,
        language=req.language,
    )
    if "error" in result:
        return {"status": "error", "error": result["error"]}
    return {"status": "ok", **result}


@router.post("/rewrite-caption-batch")
async def api_rewrite_batch(req: RewriteBatchRequest):
    """Rewrite caption for multiple pages (each gets tailored hashtags)."""
    from backend.services.facebook import get_pages

    all_pages = await get_pages(status="active")
    selected = [p for p in all_pages if p["id"] in req.page_ids]

    if not selected:
        return {"status": "error", "error": "No matching pages found"}

    results = await rewrite_caption_batch(
        original_caption=req.original_caption,
        pages=selected,
        language=req.language,
    )
    return {"status": "ok", "results": results, "count": len(results)}


class SpinCaptionsRequest(BaseModel):
    base_caption: str = ""
    page_ids: list[int] = []
    video_title: str = ""
    language: str = "en"


@router.post("/spin-captions")
async def api_spin_captions(req: SpinCaptionsRequest):
    """Generate N unique caption spins in a single GPT call."""
    if not req.page_ids:
        return {"status": "error", "error": "Select at least 1 page"}

    result = await spin_captions(
        base_caption=req.base_caption,
        page_ids=req.page_ids,
        video_title=req.video_title,
        language=req.language,
    )
    if "error" in result:
        return {"status": "error", "error": result["error"]}
    return {"status": "ok", **result}

