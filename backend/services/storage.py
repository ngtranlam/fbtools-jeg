"""Storage management — auto-cleanup old videos to save disk space."""

from __future__ import annotations

import logging
from pathlib import Path
from datetime import datetime, timedelta

from backend.database import get_db, get_setting
from backend.config import DOWNLOADS_DIR, VARIANTS_DIR

log = logging.getLogger(__name__)


async def get_storage_stats() -> dict:
    """Get current storage usage statistics."""

    def dir_size(path: Path) -> int:
        total = 0
        if path.exists():
            for f in path.rglob("*"):
                if f.is_file():
                    total += f.stat().st_size
        return total

    downloads_size = dir_size(DOWNLOADS_DIR)
    variants_size = dir_size(VARIANTS_DIR)
    total = downloads_size + variants_size

    db = await get_db()
    vc = await db.execute("SELECT COUNT(*) as cnt FROM videos")
    video_count = (await vc.fetchone())["cnt"]

    varc = await db.execute("SELECT COUNT(*) as cnt FROM variants")
    variant_count = (await varc.fetchone())["cnt"]

    return {
        "downloads_size_mb": round(downloads_size / 1024 / 1024, 1),
        "variants_size_mb": round(variants_size / 1024 / 1024, 1),
        "total_size_mb": round(total / 1024 / 1024, 1),
        "total_size_gb": round(total / 1024 / 1024 / 1024, 2),
        "video_count": video_count,
        "variant_count": variant_count,
    }


async def cleanup_old_files() -> dict:
    """Remove old video files based on configured policies."""
    cleanup_source = (await get_setting("auto_cleanup_source_after_spoof", "true")) == "true"
    cleanup_days = int(await get_setting("auto_cleanup_variant_days", "7"))
    stats = {"source_deleted": 0, "variants_deleted": 0, "space_freed_mb": 0}

    db = await get_db()

    # 1. Delete source videos that have been spoofed (variants exist)
    if cleanup_source:
        cursor = await db.execute(
            """SELECT DISTINCT v.id, v.filepath FROM videos v
               INNER JOIN variants var ON var.video_id = v.id
               WHERE var.status IN ('posted', 'ready')"""
        )
        sources = await cursor.fetchall()
        for src in sources:
            path = Path(src["filepath"])
            if path.exists():
                size = path.stat().st_size
                path.unlink()
                stats["source_deleted"] += 1
                stats["space_freed_mb"] += size / 1024 / 1024
                log.info(f"Deleted source video: {path}")

    # 2. Delete variants that were posted more than X days ago
    cutoff = (datetime.now() - timedelta(days=cleanup_days)).isoformat()
    cursor = await db.execute(
        """SELECT var.id, var.filepath FROM variants var
           INNER JOIN posts p ON p.variant_id = var.id
           WHERE p.status = 'posted' AND p.posted_at < ?
             AND var.status != 'deleted'""",
        (cutoff,),
    )
    old_variants = await cursor.fetchall()
    for var in old_variants:
        path = Path(var["filepath"])
        if path.exists():
            size = path.stat().st_size
            path.unlink()
            stats["variants_deleted"] += 1
            stats["space_freed_mb"] += size / 1024 / 1024
        await db.execute(
            "UPDATE variants SET status = 'deleted' WHERE id = ?", (var["id"],)
        )

    await db.commit()
    stats["space_freed_mb"] = round(stats["space_freed_mb"], 1)
    log.info(f"Cleanup complete: {stats}")
    return stats


async def manual_cleanup() -> dict:
    """Force cleanup — delete orphaned files, old variants, and source videos."""
    stats = {
        "source_deleted": 0,
        "variants_deleted": 0,
        "orphaned_deleted": 0,
        "space_freed_mb": 0.0,
    }
    db = await get_db()

    # Phase 1: Standard policy-based cleanup
    policy_result = await cleanup_old_files()
    stats["source_deleted"] += policy_result["source_deleted"]
    stats["variants_deleted"] += policy_result["variants_deleted"]
    stats["space_freed_mb"] += policy_result["space_freed_mb"]

    # Phase 2: Delete orphaned files on disk not tracked in database
    video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".ts", ".flv", ".wmv"}

    # Orphaned downloads
    if DOWNLOADS_DIR.exists():
        cursor = await db.execute("SELECT filepath FROM videos")
        db_paths = {row["filepath"] for row in await cursor.fetchall()}
        for f in DOWNLOADS_DIR.rglob("*"):
            if f.is_file() and f.suffix.lower() in video_exts:
                if str(f) not in db_paths and str(f.resolve()) not in db_paths:
                    try:
                        size = f.stat().st_size
                        f.unlink()
                        stats["orphaned_deleted"] += 1
                        stats["space_freed_mb"] += size / 1024 / 1024
                        log.info(f"Deleted orphaned download: {f}")
                    except OSError as e:
                        log.warning(f"Failed to delete {f}: {e}")

    # Orphaned variants
    if VARIANTS_DIR.exists():
        cursor = await db.execute("SELECT filepath FROM variants WHERE status != 'deleted'")
        db_paths = {row["filepath"] for row in await cursor.fetchall()}
        for f in VARIANTS_DIR.rglob("*"):
            if f.is_file() and f.suffix.lower() in video_exts:
                if str(f) not in db_paths and str(f.resolve()) not in db_paths:
                    try:
                        size = f.stat().st_size
                        f.unlink()
                        stats["orphaned_deleted"] += 1
                        stats["space_freed_mb"] += size / 1024 / 1024
                        log.info(f"Deleted orphaned variant: {f}")
                    except OSError as e:
                        log.warning(f"Failed to delete {f}: {e}")

    # Phase 3: Clean empty subdirectories
    for base_dir in [DOWNLOADS_DIR, VARIANTS_DIR]:
        if base_dir.exists():
            for d in sorted(base_dir.rglob("*"), reverse=True):
                if d.is_dir() and not any(d.iterdir()):
                    try:
                        d.rmdir()
                    except OSError:
                        pass

    # Phase 4: Delete DB variants marked as 'deleted' that still have files
    cursor = await db.execute("SELECT id, filepath FROM variants WHERE status = 'deleted'")
    deleted_rows = await cursor.fetchall()
    for row in deleted_rows:
        path = Path(row["filepath"])
        if path.exists():
            try:
                size = path.stat().st_size
                path.unlink()
                stats["variants_deleted"] += 1
                stats["space_freed_mb"] += size / 1024 / 1024
            except OSError:
                pass

    stats["space_freed_mb"] = round(stats["space_freed_mb"], 1)
    log.info(f"Manual cleanup complete: {stats}")
    return stats
