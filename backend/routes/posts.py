"""API routes for publishing Reels and managing posts."""

from __future__ import annotations

import logging
import traceback
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database import get_db
from backend.services.publisher import publish_to_platform
from backend.services import publish_queue

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/posts", tags=["posts"])


class PublishRequest(BaseModel):
    variant_id: int | None = None
    variant_filepath: str | None = None
    page_ids: list[int] = []  # Facebook pages
    caption: str = ""
    captions: dict[int, str] | None = None  # {page_id: spun_caption} for content spinning
    first_comment: str | None = None  # Auto first-comment after publish
    comment_image_url: str | None = None  # Image URL to attach to first comment
    schedule_at: str | None = None  # ISO format, None = publish now
    # Multi-platform fields
    platform: str = "facebook"  # facebook | pinterest | youtube
    channel_ids: list[int] = []  # Pinterest/YouTube channel IDs
    board_id: str = ""  # Pinterest board
    youtube_title: str = ""  # YouTube video title
    youtube_tags: list[str] = []  # YouTube tags
    youtube_privacy: str = "public"  # public | unlisted | private
    made_for_kids: bool = False  # YouTube COPPA


async def _target_name(db, platform: str, target_id) -> str:
    """Ten Page / kenh, chi de hien trong hang doi cho de doc."""
    try:
        if platform == "facebook":
            c = await db.execute("SELECT page_name FROM pages WHERE id = ?", (target_id,))
        else:
            c = await db.execute("SELECT name FROM channels WHERE id = ?", (target_id,))
        row = await c.fetchone()
        return (row[0] if row else "") or ""
    except Exception:
        return ""


@router.post("/publish")
async def publish_to_pages(req: PublishRequest):
    """Dang video len mot hoac nhieu Page — ngay bay gio hoac hen gio.

    "Ngay bay gio" khong con nghia la ban het cung luc: moi bai duoc xep vao
    hang doi tuan tu, cach nhau 60-120 giay ngau nhien.
    """
    try:
        db = await get_db()
        filepath = None

        # Try DB lookup first
        if req.variant_id:
            cursor = await db.execute("SELECT * FROM variants WHERE id = ?", (req.variant_id,))
            variant = await cursor.fetchone()
            if variant:
                filepath = variant["filepath"]

        # Fallback to direct filepath
        if not filepath and req.variant_filepath:
            filepath = req.variant_filepath

        if not filepath or not Path(filepath).exists():
            raise HTTPException(status_code=404, detail=f"Video file not found: {filepath}")

        # Normalize schedule time
        schedule_normalized = None
        if req.schedule_at:
            try:
                dt = datetime.fromisoformat(req.schedule_at.replace('Z', '+00:00'))
                schedule_normalized = dt.strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, AttributeError):
                schedule_normalized = req.schedule_at
            log.info(f"Scheduling post: raw='{req.schedule_at}' → normalized='{schedule_normalized}'")

        import json as _json
        results = []

        # ── Build publish targets ──────────────────────────────
        targets = []  # (platform, target_id, caption, extra_kwargs)

        # Facebook pages
        for page_id in req.page_ids:
            pc = await db.execute("SELECT id FROM pages WHERE id = ?", (page_id,))
            page_row = await pc.fetchone()
            if not page_row:
                results.append({"page_id": page_id, "platform": "facebook", "status": "error", "error": "Page not found"})
                continue
            page_caption = (req.captions or {}).get(page_id, req.caption)
            targets.append(("facebook", page_id, page_caption, {}))

        # Pinterest channels
        for ch_id in req.channel_ids:
            cc = await db.execute("SELECT platform FROM channels WHERE id = ?", (ch_id,))
            ch_row = await cc.fetchone()
            if not ch_row:
                results.append({"channel_id": ch_id, "platform": "unknown", "status": "error", "error": "Channel not found"})
                continue
            platform = ch_row["platform"]
            extra = {}
            if platform == "pinterest":
                extra = {"board_id": req.board_id, "title": req.youtube_title or req.caption[:100]}
            elif platform == "youtube":
                extra = {
                    "youtube_title": req.youtube_title or req.caption[:100],
                    "youtube_tags": req.youtube_tags,
                    "youtube_privacy": req.youtube_privacy,
                    "made_for_kids": req.made_for_kids,
                }
            targets.append((platform, ch_id, req.caption, extra))

        # ── Publish or schedule each target ────────────────────
        for platform, target_id, target_caption, extra_kwargs in targets:
            extra_json = _json.dumps(extra_kwargs) if extra_kwargs else "{}"

            if schedule_normalized:
                # Schedule for later
                page_id_val = target_id if platform == "facebook" else None
                channel_id_val = target_id if platform != "facebook" else None
                await db.execute(
                    """INSERT INTO posts (page_id, channel_id, platform, variant_id, caption, filepath,
                       first_comment, comment_image_url, extra_data, status, scheduled_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'scheduled', ?)""",
                    (page_id_val, channel_id_val, platform, req.variant_id, target_caption,
                     filepath, req.first_comment or "", req.comment_image_url or "", extra_json, schedule_normalized),
                )
                await db.commit()
                results.append({"target_id": target_id, "platform": platform, "status": "scheduled", "scheduled_at": schedule_normalized})
            else:
                # Dang ngay -> KHONG dang thang o day nua.
                #
                # Truoc day vong lap nay ban lien tiep tung Page mot, khong nghi
                # giay nao: hang chuc Page cung dang mot video trong vai giay la
                # dau hieu may chay tu dong ro nhat. Nay moi bai duoc xep vao
                # hang doi tuan tu, moi bai cach nhau 60-120 giay ngau nhien.
                #
                # Xep hang xong tra ve ngay, khong bat trinh duyet cho — dang 20
                # Page voi khoang nghi nay mat 20-40 phut.
                try:
                    q = await publish_queue.queue_post(
                        platform=platform,
                        target_id=target_id,
                        filepath=filepath,
                        caption=target_caption,
                        variant_id=req.variant_id,
                        extra=extra_kwargs,
                        first_comment=req.first_comment or "",
                        comment_image_url=req.comment_image_url or "",
                        target_name=await _target_name(db, platform, target_id),
                    )
                    results.append({
                        "target_id": target_id,
                        "platform": platform,
                        "status": "queued",
                        "position": q["position"],
                        "post_id": q["post_id"],
                    })
                except Exception as e:
                    log.error(f"Khong xep duoc vao hang doi {platform}/{target_id}: {e}")
                    results.append({"target_id": target_id, "platform": platform,
                                    "status": "failed", "error": str(e)})

        return {"status": "ok", "results": results}

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Publish endpoint error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_posts(
    page_id: int | None = None,
    status: str | None = None,
    viral_level: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    db = await get_db()
    query = """SELECT p.*, pg.page_name, pg.avatar_url, pg.store_url,
                      v.filename as variant_filename
               FROM posts p
               JOIN pages pg ON p.page_id = pg.id
               LEFT JOIN variants v ON p.variant_id = v.id
               WHERE 1=1"""
    params = []

    if page_id:
        query += " AND p.page_id = ?"
        params.append(page_id)
    if status:
        query += " AND p.status = ?"
        params.append(status)
    if viral_level:
        if viral_level == "any":
            query += " AND p.viral_level != 'none'"
        else:
            query += " AND p.viral_level = ?"
            params.append(viral_level)

    # Count total
    count_query = query.replace(
        "SELECT p.*, pg.page_name, pg.avatar_url, pg.store_url,\n                      v.filename as variant_filename",
        "SELECT COUNT(*) as cnt",
    )
    count_cursor = await db.execute(count_query, params)
    total = (await count_cursor.fetchone())["cnt"]

    query += " ORDER BY p.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    posts = []
    for row in rows:
        posts.append({
            "id": row["id"],
            "page_id": row["page_id"],
            "page_name": row["page_name"],
            "avatar_url": row["avatar_url"],
            "variant_filename": row["variant_filename"],
            "fb_post_id": row["fb_post_id"],
            "caption": row["caption"],
            "status": row["status"],
            "scheduled_at": row["scheduled_at"],
            "posted_at": row["posted_at"],
            "views_count": row["views_count"],
            "likes_count": row["likes_count"],
            "comments_count": row["comments_count"],
            "shares_count": row["shares_count"],
            "viral_level": row["viral_level"],
            "error_message": row["error_message"],
            "created_at": row["created_at"],
        })

    return {"status": "ok", "posts": posts, "total": total}


@router.delete("/{post_id}")
async def cancel_post(post_id: int):
    db = await get_db()
    cursor = await db.execute("SELECT status FROM posts WHERE id = ?", (post_id,))
    post = await cursor.fetchone()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post["status"] != "scheduled":
        raise HTTPException(status_code=400, detail="Only scheduled posts can be cancelled")

    await db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    await db.commit()
    return {"status": "ok"}


@router.get("/schedule-debug")
async def schedule_debug():
    """Debug: show scheduled posts and server time (read-only, no publishing)."""
    db = await get_db()
    cursor = await db.execute(
        """SELECT id, page_id, status, scheduled_at,
                  datetime(scheduled_at) as parsed_schedule,
                  datetime('now') as server_utc_now,
                  CASE WHEN datetime(scheduled_at) <= datetime('now')
                       THEN 'READY' ELSE 'WAITING' END as publish_status
           FROM posts WHERE status = 'scheduled'
           ORDER BY scheduled_at"""
    )
    pending = [dict(row) for row in await cursor.fetchall()]

    return {
        "status": "ok",
        "server_utc_now": (await (await db.execute("SELECT datetime('now') as t")).fetchone())["t"],
        "scheduled_posts": pending,
        "total_pending": len(pending),
    }

@router.get("/analytics")
async def posts_analytics(days: int = 7):
    """Get analytics data for charts."""
    db = await get_db()

    daily_cursor = await db.execute(
        f"""SELECT date(posted_at) as day,
                   SUM(views_count) as views,
                   COUNT(*) as posts
            FROM posts
            WHERE posted_at >= date('now', '-{days} days')
              AND status = 'posted'
            GROUP BY day ORDER BY day"""
    )
    daily = [dict(row) for row in await daily_cursor.fetchall()]

    top_pages_cursor = await db.execute(
        f"""SELECT pg.page_name, SUM(p.views_count) as total_views, COUNT(p.id) as post_count
            FROM posts p JOIN pages pg ON p.page_id = pg.id
            WHERE p.posted_at >= date('now', '-{days} days')
            GROUP BY p.page_id
            ORDER BY total_views DESC LIMIT 10"""
    )
    top_pages = [dict(row) for row in await top_pages_cursor.fetchall()]

    top_viral_cursor = await db.execute(
        f"""SELECT p.views_count, p.likes_count, p.shares_count, p.viral_level,
                   pg.page_name, p.fb_post_id, p.posted_at, p.caption
            FROM posts p JOIN pages pg ON p.page_id = pg.id
            WHERE p.viral_level != 'none'
            ORDER BY p.views_count DESC LIMIT 10"""
    )
    top_viral = [dict(row) for row in await top_viral_cursor.fetchall()]

    return {
        "daily_stats": daily,
        "top_pages": top_pages,
        "top_viral": top_viral,
    }


@router.get("/queue")
async def get_publish_queue():
    """Tinh trang hang doi dang bai."""
    return {"status": "ok", **publish_queue.status()}


@router.post("/queue/cancel")
async def cancel_publish_queue():
    """Bo moi bai con dang cho. Bai dang dang do van chay not."""
    removed = await publish_queue.cancel_all()
    return {"status": "ok", "removed": removed}
