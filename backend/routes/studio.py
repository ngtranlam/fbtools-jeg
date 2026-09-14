"""API routes cho Video Studio — ghép clip, chuyển cảnh, text, render hàng loạt."""

from __future__ import annotations

import logging
import traceback
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend.config import TEMP_DIR
from backend.services import studio

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/studio", tags=["studio"])


# ══ Cấu hình khả dụng ══════════════════════════════════════

@router.get("/options")
async def api_options():
    """Danh sách hiệu ứng chuyển cảnh, bộ màu, khung hình cho UI."""
    return {
        "status": "ok",
        "transitions": studio.TRANSITIONS,
        "looks": studio.EFFECT_LOOKS,
        "canvas_presets": studio.CANVAS_PRESETS,
        "audio_tune_presets": studio.AUDIO_TUNE_PRESETS,
        "has_font": bool(studio.resolve_font("bold")),
    }


class AudioPreviewRequest(BaseModel):
    asset_id: int
    start: float = 0.0
    duration: float = 10.0
    tune: dict | None = None
    raw: bool = False


@router.post("/audio-preview")
async def api_audio_preview(req: AudioPreviewRequest):
    """Nghe thử tiếng gốc sau khi tinh chỉnh, không cần ghép cả video."""
    from fastapi.responses import FileResponse
    from starlette.background import BackgroundTask

    result = await studio.build_audio_preview(
        asset_id=req.asset_id, start=req.start, duration=req.duration,
        tune=req.tune, raw=req.raw,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    path = Path(result["path"])
    return FileResponse(
        str(path),
        media_type="audio/mpeg",
        background=BackgroundTask(path.unlink, missing_ok=True),
    )


# ══ Assets ═════════════════════════════════════════════════

@router.post("/assets/upload")
async def api_upload_asset(file: UploadFile = File(...), kind: str = "video"):
    """Upload clip hoặc nhạc nền vào kho Studio."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Chưa chọn file")

    if kind not in ("video", "audio"):
        kind = "video"

    temp_path = TEMP_DIR / f"studio_upload_{file.filename}"
    try:
        content = await file.read()
        temp_path.write_bytes(content)
    except Exception as e:
        log.error("Lưu file tạm thất bại: %s", e)
        raise HTTPException(status_code=400, detail=f"Không lưu được file: {e}")

    try:
        asset = await studio.save_asset(temp_path, file.filename, kind=kind)
        log.info("Studio asset added: %s (%s)", asset["name"], kind)
        return {"status": "ok", "asset": asset}
    except Exception as e:
        temp_path.unlink(missing_ok=True)
        log.error("Thêm asset thất bại: %s\n%s", e, traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))


class ImportAssetRequest(BaseModel):
    filepath: str
    name: str = ""


@router.post("/assets/import")
async def api_import_asset(req: ImportAssetRequest):
    """Đưa video từ thư viện tải về / biến thể vào kho Studio."""
    try:
        asset = await studio.import_from_library(req.filepath, req.name)
        return {"status": "ok", "asset": asset}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.error("Import asset thất bại: %s", e)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/assets")
async def api_list_assets(kind: str | None = None):
    assets = await studio.list_assets(kind)
    return {"status": "ok", "assets": assets}


@router.delete("/assets/{asset_id}")
async def api_delete_asset(asset_id: int):
    ok = await studio.delete_asset(asset_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Không tìm thấy asset")
    return {"status": "ok"}


# ══ Dự án ══════════════════════════════════════════════════

class ProjectRequest(BaseModel):
    name: str = "Dự án mới"
    timeline: dict = Field(default_factory=dict)


@router.post("/projects")
async def api_create_project(req: ProjectRequest):
    project = await studio.create_project(req.name, req.timeline)
    return {"status": "ok", "project": project}


@router.get("/projects")
async def api_list_projects(limit: int = 50):
    projects = await studio.list_projects(limit)
    return {"status": "ok", "projects": projects}


@router.get("/projects/{project_id}")
async def api_get_project(project_id: int):
    project = await studio.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Không tìm thấy dự án")
    return {"status": "ok", "project": project}


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    timeline: dict | None = None


@router.put("/projects/{project_id}")
async def api_update_project(project_id: int, req: UpdateProjectRequest):
    project = await studio.update_project(project_id, req.name, req.timeline)
    if not project:
        raise HTTPException(status_code=404, detail="Không tìm thấy dự án")
    return {"status": "ok", "project": project}


@router.delete("/projects/{project_id}")
async def api_delete_project(project_id: int):
    ok = await studio.delete_project(project_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Không tìm thấy dự án")
    return {"status": "ok"}


class ComposeRequest(BaseModel):
    timeline: dict | None = None


@router.post("/projects/{project_id}/compose")
async def api_compose(project_id: int, req: ComposeRequest):
    """Ghép timeline thành 1 video base để xem trước."""
    try:
        result = await studio.compose_project(project_id, req.timeline)
    except Exception as e:
        log.error("Compose lỗi: %s\n%s", e, traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

    if "error" in result:
        return {"status": "error", "error": result["error"]}
    return {"status": "ok", **result}


class HookPlanRequest(BaseModel):
    timeline: dict | None = None
    count: int = 10


@router.post("/projects/{project_id}/hook-plan")
async def api_hook_plan(project_id: int, req: HookPlanRequest):
    """Xem trước: N biến thể sẽ lấy đoạn nào của clip nào."""
    result = await studio.preview_hook_plan(project_id, req.timeline, req.count)
    if "error" in result:
        return {"status": "error", "error": result["error"]}
    return {"status": "ok", **result}


class HookPreviewRequest(BaseModel):
    timeline: dict | None = None
    idx: int = 1
    count: int = 10


@router.post("/projects/{project_id}/hook-preview")
async def api_hook_preview(project_id: int, req: HookPreviewRequest):
    """Ghép thật một biến thể để xem thử trước khi render cả loạt."""
    try:
        result = await studio.preview_hook_variant(
            project_id, req.timeline, req.idx, req.count)
    except Exception as e:
        log.error("Ghép thử lỗi: %s\n%s", e, traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

    if "error" in result:
        return {"status": "error", "error": result["error"]}
    return {"status": "ok", **result}


# ══ Render hàng loạt ═══════════════════════════════════════

class BatchRequest(BaseModel):
    count: int = 10
    look_ids: list[str] = Field(default_factory=list)
    music_asset_ids: list[int] = Field(default_factory=list)
    keep_original_audio: bool = False
    music_volume: float = 1.0


@router.post("/projects/{project_id}/batch")
async def api_batch_render(project_id: int, req: BatchRequest):
    """Render N biến thể từ video base — mỗi bản khác nhạc, khác màu, khác vân tay."""
    result = await studio.start_batch_render(
        project_id=project_id,
        count=req.count,
        look_ids=req.look_ids,
        music_asset_ids=req.music_asset_ids,
        keep_original_audio=req.keep_original_audio,
        music_volume=req.music_volume,
    )
    # Job hợp lệ luôn có job_id; khi lỗi thì chỉ trả về khoá "error".
    # (Không dùng `"error" in result` vì bản thân job cũng mang khoá error rỗng.)
    if not result.get("job_id"):
        return {"status": "error", "error": result.get("error") or "Không khởi động được render"}
    return {"status": "ok", "job": result}


@router.get("/jobs")
async def api_list_jobs():
    return {"status": "ok", "jobs": studio.list_batch_jobs()}


@router.get("/jobs/{job_id}")
async def api_get_job(job_id: str):
    job = studio.get_batch_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy job")
    return {"status": "ok", "job": job}


@router.get("/renders")
async def api_list_renders(project_id: int | None = None, job_id: str | None = None):
    renders = await studio.list_renders(project_id, job_id)
    return {"status": "ok", "renders": renders}


# ══ Xuất biến thể ra máy ═══════════════════════════════════

class ExportRequest(BaseModel):
    export_path: str
    job_id: str = ""
    project_id: int | None = None
    create_subfolder: bool = True


@router.post("/export")
async def api_export(req: ExportRequest):
    """Chép toàn bộ biến thể đã render sang một thư mục trên máy."""
    if not req.export_path.strip():
        raise HTTPException(status_code=400, detail="Chưa chọn thư mục lưu")

    result = await studio.export_renders(
        export_path=req.export_path,
        job_id=req.job_id or None,
        project_id=req.project_id,
        create_subfolder=req.create_subfolder,
    )
    if "error" in result:
        return {"status": "error", "error": result["error"]}
    return {"status": "ok", **result}


@router.get("/renders/{render_id}/download")
async def api_download_render(render_id: int):
    """Tải một biến thể về máy."""
    from fastapi.responses import FileResponse

    render = await studio.get_render(render_id)
    if not render:
        raise HTTPException(status_code=404, detail="Không tìm thấy biến thể")

    path = Path(render["filepath"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="File đã bị xoá khỏi ổ đĩa")

    return FileResponse(str(path), media_type="video/mp4", filename=path.name)


@router.get("/export/zip")
async def api_export_zip(job_id: str = "", project_id: int | None = None):
    """Gói toàn bộ biến thể thành một file ZIP để tải về."""
    from fastapi.responses import FileResponse
    from starlette.background import BackgroundTask

    result = await studio.build_renders_zip(job_id or None, project_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    zip_path = Path(result["zip_path"])
    return FileResponse(
        str(zip_path),
        media_type="application/zip",
        filename=result["filename"],
        # Xoá file tạm sau khi trình duyệt tải xong
        background=BackgroundTask(zip_path.unlink, missing_ok=True),
    )


class OpenFolderRequest(BaseModel):
    path: str


@router.post("/open-folder")
async def api_open_folder(req: OpenFolderRequest):
    """Mở thư mục vừa xuất bằng trình quản lý file của hệ điều hành."""
    import os
    import platform
    import subprocess

    target = Path(req.path)
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=400, detail="Thư mục không tồn tại")

    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(str(target))                    # type: ignore[attr-defined]
        elif system == "Darwin":
            subprocess.Popen(["open", str(target)])      # Finder
        else:
            subprocess.Popen(["xdg-open", str(target)])  # Linux
    except (OSError, AttributeError) as e:
        log.warning("Không mở được thư mục %s: %s", target, e)
        raise HTTPException(status_code=400, detail=f"Không mở được thư mục: {e}")

    return {"status": "ok"}


# ══ Đăng hàng loạt lên Fanpage ═════════════════════════════

class DistributeRequest(BaseModel):
    job_id: str = ""
    project_id: int | None = None
    page_ids: list[int] = Field(default_factory=list)
    caption: str = ""
    captions: dict[str, str] | None = None   # {page_id: caption riêng}
    first_comment: str = ""
    comment_image_url: str = ""
    mode: str = "round_robin"                 # round_robin | one_each | all_same
    schedule_start: str | None = None         # ISO — bài đầu tiên
    interval_minutes: int = 0                 # giãn cách giữa các bài
    render_ids: list[int] = Field(default_factory=list)   # để trống = dùng tất cả


@router.post("/distribute")
async def api_distribute(req: DistributeRequest):
    """Phân phối các biến thể đã render sang nhiều Fanpage.

    Mỗi page nhận một biến thể KHÁC nhau để tránh trùng nội dung giữa các page.
    """
    from datetime import datetime, timedelta

    from backend.database import get_db
    from backend.routes.posts import PublishRequest, publish_to_pages

    if not req.page_ids:
        return {"status": "error", "error": "Chưa chọn Fanpage nào"}

    renders = await studio.list_renders(req.project_id, req.job_id or None)
    renders = [r for r in renders if Path(r["filepath"]).exists()]

    # Người dùng chọn cụ thể bản nào thì chỉ dùng những bản đó
    if req.render_ids:
        chosen = set(req.render_ids)
        renders = [r for r in renders if r["id"] in chosen]

    if not renders:
        return {"status": "error", "error": "Chưa chọn biến thể nào để đăng"}

    db = await get_db()
    schedule_base = None
    if req.schedule_start:
        try:
            schedule_base = datetime.fromisoformat(req.schedule_start.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            schedule_base = None

    results = []
    for i, page_id in enumerate(req.page_ids):
        if req.mode == "all_same":
            render = renders[0]
        else:
            render = renders[i % len(renders)]

        caption = (req.captions or {}).get(str(page_id), req.caption)

        schedule_at = None
        if schedule_base:
            schedule_at = (schedule_base + timedelta(
                minutes=req.interval_minutes * i
            )).isoformat()

        try:
            pub = await publish_to_pages(PublishRequest(
                variant_id=render.get("variant_id"),
                variant_filepath=render["filepath"],
                page_ids=[page_id],
                caption=caption,
                first_comment=req.first_comment or None,
                comment_image_url=req.comment_image_url or None,
                schedule_at=schedule_at,
                platform="facebook",
            ))
            page_result = (pub.get("results") or [{}])[0]
            results.append({
                "page_id": page_id,
                "variant": render["filename"],
                **page_result,
            })
        except HTTPException as e:
            results.append({"page_id": page_id, "variant": render["filename"],
                            "status": "failed", "error": e.detail})
        except Exception as e:
            log.error("Distribute lỗi cho page %s: %s", page_id, e)
            results.append({"page_id": page_id, "variant": render["filename"],
                            "status": "failed", "error": str(e)})

    posted = sum(1 for r in results
                 if r.get("status") in ("posted", "scheduled", "queued"))
    return {"status": "ok", "results": results, "posted": posted,
            "total": len(req.page_ids)}
