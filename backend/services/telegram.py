"""Telegram alerting service for viral video notifications and daily reports."""

from __future__ import annotations

import logging
from datetime import datetime

import httpx

from backend.database import get_db, get_setting

log = logging.getLogger(__name__)
TELEGRAM_API = "https://api.telegram.org"
TIMEOUT = httpx.Timeout(30.0, connect=10.0)

VIRAL_EMOJI = {
    "catching": "🟡",
    "viral": "🟠",
    "super_viral": "🔴",
}

VIRAL_LABEL = {
    "catching": "Cắn View (>10K)",
    "viral": "Viral (>100K)",
    "super_viral": "Siêu Viral (>1M)",
}


async def _send_message(text: str, parse_mode: str = "HTML") -> bool:
    bot_token = await get_setting("telegram_bot_token")
    chat_id = await get_setting("telegram_chat_id")
    if not bot_token or not chat_id:
        log.warning("Telegram bot_token or chat_id not configured")
        return False

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{TELEGRAM_API}/bot{bot_token}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False,
        })
        if r.status_code != 200:
            log.error(f"Telegram send failed: {r.text}")
            return False
    return True


async def send_viral_alert(post: dict, level: str) -> bool:
    """Send a viral alert to Telegram."""
    emoji = VIRAL_EMOJI.get(level, "🔵")
    label = VIRAL_LABEL.get(level, level)

    text = (
        f"{emoji} <b>VIRAL ALERT — {label}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📄 <b>Page:</b> {post.get('page_name', 'N/A')}\n"
        f"👁️ <b>Views:</b> {post.get('views_count', 0):,}\n"
        f"❤️ <b>Likes:</b> {post.get('likes_count', 0):,}\n"
        f"💬 <b>Comments:</b> {post.get('comments_count', 0):,}\n"
        f"🔄 <b>Shares:</b> {post.get('shares_count', 0):,}\n"
    )

    store_url = post.get("store_url", "")
    if store_url:
        text += f"🏪 <b>Store:</b> {store_url}\n"

    fb_post_id = post.get("fb_post_id", "")
    if fb_post_id:
        text += f"🔗 <a href='https://facebook.com/{fb_post_id}'>Xem bài đăng</a>\n"

    auto_comment = post.get("auto_comment_sent", False)
    if auto_comment:
        text += f"✅ Đã tự động comment link sản phẩm\n"

    text += f"⏰ {datetime.now().strftime('%H:%M %d/%m/%Y')}"

    return await _send_message(text)


async def send_page_growth_alert(data: dict) -> bool:
    """Send page growth/metrics alert to Telegram."""
    follower_delta = data.get("follower_delta", 0)
    views_delta = data.get("views_delta", 0)

    # Choose emoji based on growth level
    if follower_delta >= 500:
        emoji = "🚀"
    elif follower_delta >= 100:
        emoji = "📈"
    else:
        emoji = "📊"

    delta_sign = "+" if follower_delta >= 0 else ""
    views_sign = "+" if views_delta >= 0 else ""

    text = (
        f"{emoji} <b>PAGE SYNC — Cập nhật tự động</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📄 <b>Page:</b> {data.get('page_name', 'N/A')}\n"
        f"👥 <b>Followers:</b> {data.get('followers_count', 0):,}"
    )

    if follower_delta != 0:
        text += f" ({delta_sign}{follower_delta:,} trong 1h)"
    text += "\n"

    text += f"👁️ <b>Views tổng:</b> {data.get('daily_views', 0):,}"
    if views_delta != 0:
        text += f" ({views_sign}{views_delta:,}/h)"
    text += "\n"

    # Total posts
    total_posts = data.get("total_posts", 0)
    if total_posts > 0:
        text += f"📝 <b>Tổng bài đã đăng:</b> {total_posts:,}\n"

    # Top video
    top_views = data.get("top_video_views", 0)
    if top_views > 0:
        text += f"🏆 <b>Video hot nhất:</b> {top_views:,} views\n"

    # Hot videos list
    hot_videos = data.get("hot_videos", [])
    if hot_videos:
        text += f"\n🔥 <b>Top videos đang tăng tốc:</b>\n"
        for i, v in enumerate(hot_videos, 1):
            vid_link = f"https://facebook.com/{v['fb_post_id']}" if v.get("fb_post_id") else ""
            text += f"  {i}. {v.get('views', 0):,} views"
            if vid_link:
                text += f" — <a href='{vid_link}'>Xem</a>"
            text += "\n"

    text += f"\n⏰ {datetime.now().strftime('%H:%M %d/%m/%Y')}"

    return await _send_message(text)


async def send_new_posts_alert(page_name: str, new_posts: list[dict]) -> bool:
    """Send alert when new posts are discovered from Facebook during sync.
    
    Each item in new_posts: {fb_id, views, description, post_type}
    """
    count = len(new_posts)
    if count == 0:
        return False

    text = (
        f"🆕 <b>POST MỚI — Phát hiện {count} bài</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📄 <b>Page:</b> {page_name}\n\n"
    )

    for i, p in enumerate(new_posts, 1):
        cap = (p.get("description", "") or "")[:80]
        if cap:
            cap = cap.replace("\n", " ")
        fb_link = f"https://facebook.com/{p['fb_id']}" if p.get("fb_id") else ""
        text += f"  {i}. <b>{p.get('post_type', 'reel').upper()}</b>"
        text += f" — {p.get('views', 0):,} views\n"
        if cap:
            text += f"     📝 {cap}\n"
        if fb_link:
            text += f"     🔗 <a href='{fb_link}'>Xem bài</a>\n"

    text += f"\n⏰ {datetime.now().strftime('%H:%M %d/%m/%Y')}"

    return await _send_message(text)


async def send_daily_report() -> bool:
    """Send daily summary report to Telegram."""
    db = await get_db()

    total_pages = await db.execute("SELECT COUNT(*) as cnt FROM pages WHERE status = 'active'")
    tp = await total_pages.fetchone()

    total_posts = await db.execute(
        "SELECT COUNT(*) as cnt FROM posts WHERE posted_at >= date('now', '-1 day')"
    )
    tpst = await total_posts.fetchone()

    total_views = await db.execute(
        "SELECT COALESCE(SUM(views_count), 0) as total FROM posts WHERE posted_at >= date('now', '-7 day')"
    )
    tv = await total_views.fetchone()

    catching = await db.execute(
        "SELECT COUNT(*) as cnt FROM viral_alerts WHERE level = 'catching' AND alerted_at >= date('now', '-1 day')"
    )
    cc = await catching.fetchone()

    viral = await db.execute(
        "SELECT COUNT(*) as cnt FROM viral_alerts WHERE level = 'viral' AND alerted_at >= date('now', '-1 day')"
    )
    vc = await viral.fetchone()

    super_viral = await db.execute(
        "SELECT COUNT(*) as cnt FROM viral_alerts WHERE level = 'super_viral' AND alerted_at >= date('now', '-1 day')"
    )
    svc = await super_viral.fetchone()

    top_cursor = await db.execute(
        """SELECT p.views_count, pg.page_name, p.fb_post_id
           FROM posts p JOIN pages pg ON p.page_id = pg.id
           WHERE p.posted_at >= date('now', '-7 day')
           ORDER BY p.views_count DESC LIMIT 5"""
    )
    top_videos = await top_cursor.fetchall()

    text = (
        f"📊 <b>BÁO CÁO NGÀY — JEG Social Tools</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 {datetime.now().strftime('%d/%m/%Y')}\n\n"
        f"📄 Pages đang hoạt động: <b>{tp['cnt']}</b>\n"
        f"📝 Bài đăng hôm nay: <b>{tpst['cnt']}</b>\n"
        f"👁️ Tổng views 7 ngày: <b>{tv['total']:,}</b>\n\n"
        f"🟡 Catching (>10K): <b>{cc['cnt']}</b>\n"
        f"🟠 Viral (>100K): <b>{vc['cnt']}</b>\n"
        f"🔴 Siêu Viral (>1M): <b>{svc['cnt']}</b>\n\n"
    )

    if top_videos:
        text += "<b>🏆 Top Videos 7 Ngày:</b>\n"
        for i, vid in enumerate(top_videos, 1):
            text += f"  {i}. {vid['page_name']} — {vid['views_count']:,} views\n"

    text += f"\n⏰ {datetime.now().strftime('%H:%M %d/%m/%Y')}"

    return await _send_message(text)


async def test_connection() -> dict:
    """Test Telegram bot connection."""
    bot_token = await get_setting("telegram_bot_token")
    if not bot_token:
        return {"ok": False, "error": "Bot token chưa được cấu hình"}

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(f"{TELEGRAM_API}/bot{bot_token}/getMe")
        if r.status_code == 200:
            data = r.json()
            return {
                "ok": True,
                "bot_name": data.get("result", {}).get("first_name", ""),
                "bot_username": data.get("result", {}).get("username", ""),
            }
        return {"ok": False, "error": r.text}
