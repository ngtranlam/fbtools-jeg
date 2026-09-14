"""API routes for Unified Inbox — comment management across all pages."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database import get_db
from backend.services.facebook import post_comment

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/inbox", tags=["inbox"])


@router.get("/comments")
async def list_comments(
    page_id: int | None = None,
    replied: int | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List inbox comments with filtering."""
    db = await get_db()
    query = """SELECT ic.*, pg.page_name, pg.avatar_url
               FROM inbox_comments ic
               JOIN pages pg ON ic.page_id = pg.id
               WHERE 1=1"""
    params = []

    if page_id:
        query += " AND ic.page_id = ?"
        params.append(page_id)
    if replied is not None:
        query += " AND ic.replied = ?"
        params.append(replied)

    # Count
    count_q = query.replace(
        "SELECT ic.*, pg.page_name, pg.avatar_url", "SELECT COUNT(*) as cnt"
    )
    cursor = await db.execute(count_q, params)
    total = (await cursor.fetchone())["cnt"]

    query += " ORDER BY ic.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    return {
        "status": "ok",
        "comments": [dict(r) for r in rows],
        "total": total,
    }


class ReplyRequest(BaseModel):
    comment_id: int  # DB id
    message: str


@router.post("/reply")
async def reply_to_comment(req: ReplyRequest):
    """Reply to a comment via Facebook Graph API."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM inbox_comments WHERE id = ?", (req.comment_id,)
    )
    comment = await cursor.fetchone()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    try:
        result = await post_comment(
            comment["page_id"], comment["fb_comment_id"], req.message
        )

        await db.execute(
            """UPDATE inbox_comments SET
                replied = 1, reply_message = ?, replied_at = datetime('now')
               WHERE id = ?""",
            (req.message, req.comment_id),
        )
        await db.commit()

        return {"status": "ok", "comment_id": result.get("id", "")}

    except Exception as e:
        log.error(f"Reply failed: {e}")
        return {"status": "error", "error": str(e)}


@router.post("/sync")
async def sync_comments():
    """Sync latest comments from all active pages."""
    import httpx

    db = await get_db()
    cursor = await db.execute("SELECT * FROM pages WHERE status = 'active'")
    pages = await cursor.fetchall()

    total_new = 0

    for page in pages:
        try:
            token = page["page_access_token"]
            fb_page_id = page["fb_page_id"]

            # Fetch recent posts
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(
                    f"https://graph.facebook.com/v21.0/{fb_page_id}/feed",
                    params={
                        "fields": "id,comments{id,from,message,created_time}",
                        "limit": 10,
                        "access_token": token,
                    },
                )

            if r.status_code != 200:
                continue

            data = r.json()
            posts_data = data.get("data", [])

            for post_data in posts_data:
                comments_data = post_data.get("comments", {}).get("data", [])
                for comment_data in comments_data:
                    fb_comment_id = comment_data.get("id", "")
                    if not fb_comment_id:
                        continue

                    commenter = comment_data.get("from", {})
                    message = comment_data.get("message", "")

                    try:
                        await db.execute(
                            """INSERT OR IGNORE INTO inbox_comments
                                (page_id, fb_post_id, fb_comment_id, commenter_name,
                                 commenter_id, message)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (
                                page["id"],
                                post_data.get("id", ""),
                                fb_comment_id,
                                commenter.get("name", ""),
                                commenter.get("id", ""),
                                message,
                            ),
                        )
                        total_new += 1
                    except Exception:
                        pass

            await db.commit()

        except Exception as e:
            log.error(f"Sync comments for page {page['id']} failed: {e}")

    return {"status": "ok", "new_comments": total_new}
