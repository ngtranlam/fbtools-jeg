"""View monitoring service — checks post insights and triggers viral alerts."""

from __future__ import annotations

import logging
from datetime import datetime

from backend.database import get_db, get_setting
from backend.services.facebook import get_reel_insights, sync_page_metrics
from backend.services.telegram import send_viral_alert, send_page_growth_alert
from backend.services.auto_comment import execute_auto_comment

log = logging.getLogger(__name__)


def _classify_viral(views: int, thresholds: dict) -> str | None:
    """Classify viral level based on view count."""
    if views >= thresholds["super_viral"]:
        return "super_viral"
    if views >= thresholds["viral"]:
        return "viral"
    if views >= thresholds["catching"]:
        return "catching"
    return None


async def check_all_posts() -> dict:
    """Check views for all recent posts and trigger alerts for viral ones."""
    thresholds = {
        "catching": int(await get_setting("viral_threshold_catching", "10000")),
        "viral": int(await get_setting("viral_threshold_viral", "100000")),
        "super_viral": int(await get_setting("viral_threshold_super_viral", "1000000")),
    }

    db = await get_db()
    cursor = await db.execute(
        """SELECT p.id, p.page_id, p.fb_post_id, p.views_count, p.viral_level,
                  p.likes_count, p.comments_count, p.shares_count,
                  pg.page_name, pg.store_url
           FROM posts p JOIN pages pg ON p.page_id = pg.id
           WHERE p.status = 'posted'
             AND p.posted_at >= datetime('now', '-7 days')
             AND p.fb_post_id != ''"""
    )
    posts = await cursor.fetchall()
    stats = {"checked": 0, "updated": 0, "alerts_sent": 0, "errors": 0}

    for post in posts:
        try:
            insights = await get_reel_insights(post["page_id"], post["fb_post_id"])
            if not insights:
                # Fallback: use existing views from DB (may have been updated by sync_page_metrics)
                db_views = post["views_count"] or 0
                if db_views > 0:
                    new_level = _classify_viral(db_views, thresholds)
                    old_level = post["viral_level"]
                    if new_level and new_level != old_level:
                        log.info(f"Fallback viral check: post {post['id']} has {db_views} views (from DB), level {old_level} -> {new_level}")
                        await db.execute(
                            "UPDATE posts SET viral_level = ? WHERE id = ?",
                            (new_level, post["id"]),
                        )
                        existing = await db.execute(
                            "SELECT id FROM viral_alerts WHERE post_id = ? AND level = ?",
                            (post["id"], new_level),
                        )
                        if not await existing.fetchone():
                            await db.execute(
                                """INSERT INTO viral_alerts (post_id, level, views_at_alert, telegram_sent)
                                   VALUES (?, ?, ?, 0)""",
                                (post["id"], new_level, db_views),
                            )
                            await db.commit()
                            alert_data = {
                                "page_name": post["page_name"],
                                "views_count": db_views,
                                "likes_count": post["likes_count"] or 0,
                                "comments_count": post["comments_count"] or 0,
                                "shares_count": post["shares_count"] or 0,
                                "store_url": post["store_url"],
                                "fb_post_id": post["fb_post_id"],
                            }
                            tg_sent = await send_viral_alert(alert_data, new_level)
                            if tg_sent:
                                await db.execute(
                                    "UPDATE viral_alerts SET telegram_sent = 1 WHERE post_id = ? AND level = ?",
                                    (post["id"], new_level),
                                )
                                stats["alerts_sent"] += 1
                continue

            stats["checked"] += 1
            new_views = insights.get("views", 0)
            new_likes = insights.get("likes", 0)
            new_comments = insights.get("comments", 0)
            new_shares = insights.get("shares", 0)

            # Update DB
            await db.execute(
                """UPDATE posts SET
                    views_count = ?, likes_count = ?, comments_count = ?,
                    shares_count = ?, last_checked_at = datetime('now')
                   WHERE id = ?""",
                (new_views, new_likes, new_comments, new_shares, post["id"]),
            )

            # Check viral level
            new_level = _classify_viral(new_views, thresholds)
            old_level = post["viral_level"]

            if new_level and new_level != old_level:
                await db.execute(
                    "UPDATE posts SET viral_level = ? WHERE id = ?",
                    (new_level, post["id"]),
                )

                existing = await db.execute(
                    "SELECT id FROM viral_alerts WHERE post_id = ? AND level = ?",
                    (post["id"], new_level),
                )
                if not await existing.fetchone():
                    await db.execute(
                        """INSERT INTO viral_alerts (post_id, level, views_at_alert, telegram_sent)
                           VALUES (?, ?, ?, 0)""",
                        (post["id"], new_level, new_views),
                    )
                    await db.commit()

                    alert_data = {
                        "page_name": post["page_name"],
                        "views_count": new_views,
                        "likes_count": new_likes,
                        "comments_count": new_comments,
                        "shares_count": new_shares,
                        "store_url": post["store_url"],
                        "fb_post_id": post["fb_post_id"],
                    }
                    tg_sent = await send_viral_alert(alert_data, new_level)

                    if tg_sent:
                        await db.execute(
                            "UPDATE viral_alerts SET telegram_sent = 1 WHERE post_id = ? AND level = ?",
                            (post["id"], new_level),
                        )
                        stats["alerts_sent"] += 1

                    if new_level == "catching":
                        import asyncio
                        asyncio.create_task(execute_auto_comment(post["id"]))

            await db.commit()
            stats["updated"] += 1

        except Exception as e:
            log.error(f"Error checking post {post['id']}: {e}")
            stats["errors"] += 1

    log.info(f"Monitor complete: {stats}")
    return stats


async def sync_all_pages() -> dict:
    """Sync metrics for all active pages and detect growth/velocity spikes.
    
    Only syncs pages with status='active'. Pages set to 'paused' are skipped.
    Alerts are only sent when there is ACTUAL CHANGE (delta-based), not on
    absolute values — this prevents Telegram spam every sync cycle.
    """
    db = await get_db()
    follower_threshold = int(await get_setting("growth_alert_followers_threshold", "50"))
    views_velocity_threshold = int(await get_setting("growth_alert_views_velocity", "5000"))

    cursor = await db.execute(
        "SELECT id, page_name, followers_count FROM pages WHERE status = 'active'"
    )
    pages = await cursor.fetchall()
    stats = {"synced": 0, "alerts_sent": 0, "skipped_paused": 0, "errors": 0}

    for page in pages:
        try:
            # Fetch live metrics from FB
            metrics = await sync_page_metrics(page["id"])
            stats["synced"] += 1

            # Get previous snapshot (most recent BEFORE this sync)
            prev_cursor = await db.execute(
                """SELECT followers_count, daily_views, top_video_views
                   FROM page_metrics_history
                   WHERE page_id = ? AND synced_at < datetime('now')
                   ORDER BY synced_at DESC LIMIT 1""",
                (page["id"],),
            )
            prev = await prev_cursor.fetchone()

            if prev:
                follower_delta = metrics["followers_count"] - prev["followers_count"]
                views_delta = metrics["daily_views"] - prev["daily_views"]
                prev_top_views = prev["top_video_views"] or 0
            else:
                # First sync — no delta, no alert
                follower_delta = 0
                views_delta = 0
                prev_top_views = 0

            # Detect velocity spikes for individual videos
            velocity_posts = []
            post_cursor = await db.execute(
                """SELECT p.id, p.fb_post_id, p.views_count, p.likes_count,
                          pg.page_name
                   FROM posts p JOIN pages pg ON p.page_id = pg.id
                   WHERE p.page_id = ? AND p.status = 'posted'
                     AND p.posted_at >= datetime('now', '-3 days')
                     AND p.fb_post_id != ''
                   ORDER BY p.views_count DESC LIMIT 5""",
                (page["id"],),
            )
            velocity_rows = await post_cursor.fetchall()

            for vp in velocity_rows:
                if vp["views_count"] > 0:
                    velocity_posts.append({
                        "fb_post_id": vp["fb_post_id"],
                        "views": vp["views_count"],
                        "likes": vp["likes_count"],
                    })

            # ══ ALERT LOGIC (delta-based only) ══
            # Only send if there is MEANINGFUL CHANGE since last sync:
            #   1. Follower growth >= threshold (default 50)
            #   2. Views velocity spike >= threshold (default 5000/cycle)
            #   3. Top video NEWLY crossed 10K (wasn't >10K before)
            top_newly_viral = (
                metrics["top_video_views"] > 10000
                and prev_top_views <= 10000
            )

            should_alert = (
                follower_delta >= follower_threshold
                or views_delta >= views_velocity_threshold
                or top_newly_viral
            )

            if should_alert:
                alert_data = {
                    "page_name": page["page_name"],
                    "followers_count": metrics["followers_count"],
                    "follower_delta": follower_delta,
                    "daily_views": metrics["daily_views"],
                    "views_delta": views_delta,
                    "total_posts": metrics.get("total_posts", 0),
                    "top_video_id": metrics["top_video_id"],
                    "top_video_views": metrics["top_video_views"],
                    "hot_videos": velocity_posts[:3],
                }
                sent = await send_page_growth_alert(alert_data)
                if sent:
                    stats["alerts_sent"] += 1
                    log.info(
                        f"Alert sent for '{page['page_name']}': "
                        f"followers={follower_delta:+d}, views={views_delta:+d}, "
                        f"top_newly_viral={top_newly_viral}"
                    )

        except Exception as e:
            log.error(f"Error syncing page {page['page_name']}: {e}")
            stats["errors"] += 1

    log.info(f"Page sync complete: {stats}")
    return stats
