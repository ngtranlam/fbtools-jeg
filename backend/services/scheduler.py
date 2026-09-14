"""Background scheduler for periodic tasks — view monitoring, scheduled posts, cleanup."""

from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from backend.database import get_db, get_setting

log = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _publish_scheduled_posts():
    """Check for posts scheduled to be published now and publish them."""
    import json as _json
    from backend.services import publish_queue

    db = await get_db()
    # Use datetime() to normalize both sides — fixes ISO 8601 'T' vs space separator mismatch
    cursor = await db.execute(
        """SELECT p.id, p.page_id, p.channel_id, p.platform, p.caption,
                  p.filepath as post_filepath, p.first_comment,
                  COALESCE(p.comment_image_url, '') as comment_image_url,
                  p.extra_data, p.scheduled_at, v.filepath as variant_filepath
           FROM posts p LEFT JOIN variants v ON p.variant_id = v.id
           WHERE p.status = 'scheduled'
             AND datetime(p.scheduled_at) <= datetime('now')"""
    )
    posts = await cursor.fetchall()
    if posts:
        log.info(f"Found {len(posts)} scheduled post(s) ready to publish")

    # Bai den gio duoc XEP VAO HANG DOI chung chu khong dang thang o day.
    # Neu tool tat mot luc roi mo lai, co the co chuc bai cung den han — dang
    # thang la ban het trong vai giay. Qua hang doi thi chung van cach nhau
    # 60-120 giay nhu moi duong dang khac.
    for post in posts:
        try:
            filepath = post["post_filepath"] or post["variant_filepath"]
            if not filepath:
                raise ValueError("Khong tim thay file video cho bai da hen gio")

            platform = post["platform"] or "facebook"
            target_id = post["page_id"] if platform == "facebook" else post["channel_id"]
            extra_kwargs = _json.loads(post["extra_data"]) if post["extra_data"] else {}

            await db.execute(
                "UPDATE posts SET status = 'queued' WHERE id = ?", (post["id"],))
            await db.commit()

            await publish_queue.enqueue({
                "post_id": post["id"],
                "platform": platform,
                "target_id": target_id,
                "filepath": filepath,
                "caption": post["caption"],
                "extra": extra_kwargs,
                "first_comment": post["first_comment"] or "",
                "comment_image_url": post["comment_image_url"] or "",
            })
            log.info("Da xep bai hen gio %s vao hang doi", post["id"])

        except Exception as e:
            log.error("Khong xep duoc bai hen gio %s: %s", post["id"], e)
            await db.execute(
                "UPDATE posts SET status = 'failed', error_message = ? WHERE id = ?",
                (str(e), post["id"]),
            )
            await db.commit()

async def _monitor_views():
    """Wrapper for monitor service."""
    from backend.services.monitor import check_all_posts
    try:
        await check_all_posts()
    except Exception as e:
        log.error(f"Monitor job failed: {e}")


async def _daily_report():
    """Wrapper for daily telegram report."""
    from backend.services.telegram import send_daily_report
    try:
        await send_daily_report()
    except Exception as e:
        log.error(f"Daily report failed: {e}")


async def _sync_pages():
    """Wrapper for hourly page metrics sync."""
    from backend.services.monitor import sync_all_pages
    try:
        stats = await sync_all_pages()
        log.info(f"Page sync completed: {stats}")
    except Exception as e:
        log.error(f"Page sync job failed: {e}")


async def _sync_spy_channels():
    """Tự động cập nhật chỉ số các kênh đối thủ đang theo dõi."""
    from backend.services.spy import auto_sync_all_channels
    try:
        stats = await auto_sync_all_channels()
        if not stats.get("skipped"):
            log.info(f"Spy auto-sync completed: {stats}")
    except Exception as e:
        log.error(f"Spy auto-sync job failed: {e}")


async def _cleanup_old_files():
    """Clean up old video files to save disk space."""
    from backend.services.storage import cleanup_old_files
    try:
        await cleanup_old_files()
    except Exception as e:
        log.error(f"Cleanup job failed: {e}")


async def start_scheduler():
    """Initialize and start the background scheduler."""
    monitor_interval = int(await get_setting("monitor_interval_minutes", "30"))
    sync_interval = int(await get_setting("sync_interval_minutes", "60"))
    report_hour = int(await get_setting("daily_report_hour", "8"))
    # Spy quét thưa hơn: mỗi lần phải gọi ra ngoài cho từng video, gọi dày dễ bị chặn
    spy_interval = int(await get_setting("spy_sync_interval_minutes", "180"))

    scheduler.add_job(
        _publish_scheduled_posts,
        trigger=IntervalTrigger(minutes=1),
        id="publish_scheduled",
        replace_existing=True,
    )

    scheduler.add_job(
        _monitor_views,
        trigger=IntervalTrigger(minutes=monitor_interval),
        id="monitor_views",
        replace_existing=True,
    )

    scheduler.add_job(
        _sync_pages,
        trigger=IntervalTrigger(minutes=sync_interval),
        id="sync_pages",
        replace_existing=True,
    )

    scheduler.add_job(
        _daily_report,
        trigger=CronTrigger(hour=report_hour, minute=0),
        id="daily_report",
        replace_existing=True,
    )

    spy_enabled = (await get_setting("spy_auto_sync_enabled", "true")).lower() == "true"
    if spy_enabled:
        scheduler.add_job(
            _sync_spy_channels,
            trigger=IntervalTrigger(minutes=spy_interval),
            id="sync_spy_channels",
            replace_existing=True,
            # Quét nhiều kênh có thể mất hàng chục phút. Không cho hai lượt chạy
            # chồng nhau, và nếu lỡ mất một lượt thì chỉ chạy bù một lần.
            max_instances=1,
            coalesce=True,
            misfire_grace_time=600,
        )

    scheduler.add_job(
        _cleanup_old_files,
        trigger=CronTrigger(hour=3, minute=0),
        id="cleanup_files",
        replace_existing=True,
    )

    scheduler.start()
    log.info(
        f"Scheduler started: monitor={monitor_interval}min, "
        f"page_sync={sync_interval}min, "
        f"spy_sync={f'{spy_interval}min' if spy_enabled else 'tat'}, "
        f"report={report_hour}:00"
    )


def reschedule_spy_sync(interval_minutes: int, enabled: bool) -> None:
    """Áp ngay nhịp mới cho việc tự động cập nhật Spy, không cần khởi động lại tool."""
    if not scheduler.running:
        return

    if not enabled:
        try:
            scheduler.remove_job("sync_spy_channels")
            log.info("Spy auto-sync disabled")
        except Exception:
            pass  # job chưa tồn tại thì thôi
        return

    scheduler.add_job(
        _sync_spy_channels,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="sync_spy_channels",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=600,
    )
    log.info(f"Spy auto-sync rescheduled: every {interval_minutes} min")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        log.info("Scheduler stopped")
