"""API routes for Facebook Page management."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services import facebook

router = APIRouter(prefix="/api/pages", tags=["pages"])


class UpdatePageRequest(BaseModel):
    store_url: str | None = None
    comment_templates: list[str] | None = None
    status: str | None = None


@router.get("")
async def list_pages(account_id: int | None = None, status: str | None = None):
    pages = await facebook.get_pages(account_id=account_id, status=status)
    return {"status": "ok", "pages": pages, "count": len(pages)}


@router.put("/{page_id}")
async def update_page(page_id: int, req: UpdatePageRequest):
    try:
        result = await facebook.update_page(
            page_id,
            store_url=req.store_url,
            comment_templates=req.comment_templates,
            status=req.status,
        )
        return {"status": "ok", "page": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats")
async def pages_stats():
    """Overall page statistics."""
    from backend.database import get_db, get_setting
    db = await get_db()

    total = await db.execute("SELECT COUNT(*) as cnt FROM pages")
    total_row = await total.fetchone()

    active = await db.execute("SELECT COUNT(*) as cnt FROM pages WHERE status = 'active'")
    active_row = await active.fetchone()

    total_views = await db.execute("SELECT COALESCE(SUM(views_count), 0) as total FROM posts")
    views_row = await total_views.fetchone()

    total_posts = await db.execute("SELECT COUNT(*) as cnt FROM posts WHERE status = 'posted'")
    posts_row = await total_posts.fetchone()

    # Get thresholds from settings
    th_catching = int(await get_setting("viral_threshold_catching", "10000"))
    th_viral = int(await get_setting("viral_threshold_viral", "100000"))
    th_super = int(await get_setting("viral_threshold_super_viral", "1000000"))

    # Count directly from posts based on actual views
    catching = await db.execute(
        "SELECT COUNT(*) as cnt FROM posts WHERE views_count >= ? AND views_count < ? AND status = 'posted'",
        (th_catching, th_viral),
    )
    catching_row = await catching.fetchone()

    viral = await db.execute(
        "SELECT COUNT(*) as cnt FROM posts WHERE views_count >= ? AND views_count < ? AND status = 'posted'",
        (th_viral, th_super),
    )
    viral_row = await viral.fetchone()

    super_viral = await db.execute(
        "SELECT COUNT(*) as cnt FROM posts WHERE views_count >= ? AND status = 'posted'",
        (th_super,),
    )
    sv_row = await super_viral.fetchone()

    return {
        "total_pages": total_row["cnt"],
        "active_pages": active_row["cnt"],
        "total_views": views_row["total"],
        "total_posts": posts_row["cnt"],
        "catching_count": catching_row["cnt"],
        "viral_count": viral_row["cnt"],
        "super_viral_count": sv_row["cnt"],
    }


@router.get("/not-posted-today")
async def pages_not_posted_today():
    """Get list of active pages that have NOT posted anything today."""
    from backend.database import get_db
    db = await get_db()

    cursor = await db.execute(
        """SELECT p.id, p.page_name, p.fb_page_id, p.followers_count,
                  p.status, a.name as account_name
           FROM pages p
           LEFT JOIN accounts a ON p.account_id = a.id
           WHERE p.status = 'active'
             AND p.id NOT IN (
                 SELECT DISTINCT page_id FROM posts
                 WHERE date(posted_at) = date('now')
                   AND status = 'posted'
             )
           ORDER BY p.page_name"""
    )
    rows = await cursor.fetchall()

    pages = []
    for r in rows:
        fb_url = f"https://facebook.com/{r['fb_page_id']}" if r["fb_page_id"] else ""
        pages.append({
            "id": r["id"],
            "page_name": r["page_name"],
            "fb_page_id": r["fb_page_id"],
            "fb_url": fb_url,
            "followers_count": r["followers_count"] or 0,
            "account_name": r["account_name"] or "N/A",
        })

    # Also get total active for the ratio
    total_active = await db.execute(
        "SELECT COUNT(*) as cnt FROM pages WHERE status = 'active'"
    )
    total_row = await total_active.fetchone()

    return {
        "status": "ok",
        "pages": pages,
        "not_posted_count": len(pages),
        "total_active": total_row["cnt"],
    }


@router.post("/sync")
async def sync_pages_now():
    """Manually trigger a page metrics sync for all active pages."""
    from backend.services.monitor import sync_all_pages
    try:
        stats = await sync_all_pages()
        return {"status": "ok", "message": "Sync completed", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-viral")
async def check_viral_now(reset_post_id: int | None = None):
    """Manually trigger viral check for all recent posts.
    Optional: reset_post_id to reset a specific post's viral_level before checking."""
    from backend.services.monitor import check_all_posts
    from backend.database import get_db
    try:
        reset_info = None
        if reset_post_id:
            db = await get_db()
            await db.execute("UPDATE posts SET viral_level = 'none' WHERE id = ?", (reset_post_id,))
            await db.execute("DELETE FROM viral_alerts WHERE post_id = ?", (reset_post_id,))
            await db.commit()
            reset_info = f"Reset post {reset_post_id} viral_level to 'none'"

        stats = await check_all_posts()
        result = {"status": "ok", "message": "Viral check completed", "stats": stats}
        if reset_info:
            result["reset"] = reset_info
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{page_id}/metrics-history")
async def get_page_metrics_history(page_id: int, limit: int = 24):
    """Get metrics history for a page (default: last 24 hours)."""
    from backend.database import get_db
    db = await get_db()
    cursor = await db.execute(
        """SELECT * FROM page_metrics_history
           WHERE page_id = ?
           ORDER BY synced_at DESC LIMIT ?""",
        (page_id, limit),
    )
    rows = await cursor.fetchall()
    return {
        "status": "ok",
        "page_id": page_id,
        "history": [dict(r) for r in rows],
        "count": len(rows),
    }


@router.get("/{page_id}/videos")
async def get_page_videos(
    page_id: int,
    sort_by: str = "views_count",
    order: str = "desc",
    limit: int = 100,
):
    """Get all videos/posts for a specific page with full stats."""
    from backend.database import get_db
    db = await get_db()

    allowed_sorts = {"views_count", "likes_count", "comments_count", "posted_at", "created_at"}
    if sort_by not in allowed_sorts:
        sort_by = "views_count"
    order_dir = "DESC" if order == "desc" else "ASC"

    # Get page info
    page_cursor = await db.execute("SELECT * FROM pages WHERE id = ?", (page_id,))
    page = await page_cursor.fetchone()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    cursor = await db.execute(
        f"""SELECT p.id, p.fb_post_id, p.caption, p.post_type, p.status,
                   p.views_count, p.likes_count, p.comments_count, p.shares_count,
                   p.viral_level, p.posted_at, p.created_at, p.last_checked_at,
                   v.filepath as variant_filepath, v.filename as variant_filename
            FROM posts p
            LEFT JOIN variants v ON v.id = p.variant_id
            WHERE p.page_id = ? AND p.status = 'posted'
            ORDER BY {sort_by} {order_dir}
            LIMIT ?""",
        (page_id, limit),
    )
    rows = await cursor.fetchall()

    return {
        "status": "ok",
        "page": dict(page),
        "videos": [dict(r) for r in rows],
        "count": len(rows),
    }


@router.get("/{page_id}/diagnose-permissions")
async def diagnose_permissions(page_id: int):
    """Kiểm tra token của Page có đủ quyền đăng bài không, và vì sao thiếu."""
    from backend.services.facebook import diagnose_page_permissions
    try:
        return {"status": "ok", "detail": await diagnose_page_permissions(page_id)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
