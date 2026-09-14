from __future__ import annotations

import shutil
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.models import SpoofRequest
from backend.services.spoofer import create_spoof_job, get_job, get_all_jobs
from backend.services.transform_profiles import list_profiles
from backend.config import VARIANTS_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/spoof", tags=["spoof"])


class ExportRequest(BaseModel):
    job_id: str
    export_path: str


@router.post("/")
async def api_start_spoof(req: SpoofRequest):
    try:
        job = await create_spoof_job(req)
        return {"success": True, "job": job.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/jobs")
async def api_list_jobs():
    jobs = get_all_jobs()
    return {"jobs": [j.model_dump() for j in jobs]}


@router.get("/jobs/{job_id}")
async def api_get_job(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job": job.model_dump()}


@router.get("/profiles")
async def api_list_profiles():
    return {"profiles": list_profiles()}


@router.post("/export")
async def api_export_variants(req: ExportRequest):
    """Export all variants from a job to a chosen folder."""
    job = get_job(req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.variants:
        raise HTTPException(status_code=400, detail="No variants to export")

    export_dir = Path(req.export_path)
    try:
        export_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot create folder: {e}")

    exported = []
    for variant in job.variants:
        src = Path(variant.filepath)
        if not src.exists():
            continue
        dest = export_dir / variant.filename
        try:
            shutil.copy2(str(src), str(dest))
            exported.append(variant.filename)
        except Exception as e:
            logger.error(f"Export error for {variant.filename}: {e}")

    return {
        "success": True,
        "exported_count": len(exported),
        "export_path": str(export_dir),
        "files": exported,
    }


@router.get("/export/browse")
async def api_browse_folders(path: str = ""):
    """List folders at a given path for folder picker."""
    if not path:
        # Điểm khởi đầu: ổ đĩa trên Windows, các thư mục quen thuộc trên macOS/Linux
        import platform
        import string

        roots = []
        if platform.system() == "Windows":
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if Path(drive).exists():
                    roots.append({"name": f"{letter}:", "path": drive, "type": "drive"})
        else:
            home = Path.home()
            candidates = [
                ("Desktop", home / "Desktop"),
                ("Downloads", home / "Downloads"),
                ("Documents", home / "Documents"),
                ("Movies", home / "Movies"),
                (home.name, home),
                ("Volumes (ổ ngoài)", Path("/Volumes")),
                ("Máy tính", Path("/")),
            ]
            for name, p in candidates:
                if p.exists() and p.is_dir():
                    roots.append({"name": name, "path": str(p), "type": "drive"})
        return {"folders": roots, "current_path": ""}

    target = Path(path)
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=400, detail="Path does not exist")

    folders = []
    try:
        for item in sorted(target.iterdir()):
            if item.is_dir() and not item.name.startswith('.'):
                try:
                    folders.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "folder",
                    })
                except PermissionError:
                    pass
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied to this folder")

    return {
        "folders": folders,
        "current_path": str(target),
        "parent_path": str(target.parent) if target.parent != target else "",
    }
