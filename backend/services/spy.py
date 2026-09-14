"""Spy service — fetch TikTok/YouTube channel videos via yt-dlp."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime

from backend.database import get_db

log = logging.getLogger(__name__)


def detect_platform(url: str) -> str:
    """Detect platform from URL."""
    url_lower = url.lower()
    if "tiktok.com" in url_lower:
        return "tiktok"
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    if "facebook.com" in url_lower or "fb.com" in url_lower or "fb.watch" in url_lower:
        return "facebook"
    return "unknown"


#: Facebook không cho quét danh sách video của trang người khác, nên kênh Facebook
#: hoạt động như một BỘ SƯU TẬP LINK: người dùng tự dán link từng video/reel vào,
#: tool chỉ lo cập nhật chỉ số và theo dõi mức tăng trưởng.
MANUAL_PLATFORMS = {"facebook"}


def normalize_channel_url(url: str) -> str:
    """Normalize channel URL for consistent storage."""
    url = url.strip().rstrip("/")
    # Trang cá nhân Facebook nằm ở dạng profile.php?id=... nên phải giữ tham số id;
    # các nền tảng khác thì bỏ hết query cho gọn.
    if "profile.php" in url.lower():
        match = re.search(r"(https?://[^?]+\?id=\d+)", url, re.IGNORECASE)
        if match:
            return match.group(1)
    return re.sub(r"\?.*$", "", url)


async def add_channel(channel_url: str, channel_name: str = "") -> dict:
    """Add a spy channel to track."""
    db = await get_db()
    url = normalize_channel_url(channel_url)
    platform = detect_platform(url)

    if platform == "unknown":
        return {"error": "URL không hợp lệ. Hỗ trợ: TikTok, YouTube, Facebook"}

    if not channel_name:
        if platform == "facebook":
            # profile.php?id=123 -> "Facebook 123", còn /tencuatrang -> "tencuatrang"
            match = re.search(r"id=(\d+)", url)
            if match:
                channel_name = f"Facebook {match.group(1)[-6:]}"
            else:
                slug = url.rstrip("/").split("/")[-1]
                channel_name = slug or "Trang Facebook"
        else:
            parts = url.rstrip("/").split("/")
            channel_name = parts[-1].replace("@", "") if parts else "Unknown"

    try:
        await db.execute(
            """INSERT INTO spy_channels (platform, channel_url, channel_name, status, created_at)
               VALUES (?, ?, ?, 'active', datetime('now'))""",
            (platform, url, channel_name),
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM spy_channels WHERE channel_url = ?", (url,))
        row = await cursor.fetchone()
        return {"success": True, "channel": dict(row)}

    except Exception as e:
        if "UNIQUE constraint" in str(e):
            return {"error": "Kênh này đã được thêm trước đó."}
        log.error(f"Add channel failed: {e}")
        return {"error": str(e)}


async def list_channels(status: str = "active") -> list[dict]:
    """List all spy channels."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM spy_channels WHERE status = ? ORDER BY created_at DESC", (status,)
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_channel(channel_id: int) -> dict | None:
    """Get a single channel by ID."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM spy_channels WHERE id = ?", (channel_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def delete_channel(channel_id: int) -> bool:
    """Delete a spy channel and its videos."""
    db = await get_db()
    await db.execute("DELETE FROM spy_channels WHERE id = ?", (channel_id,))
    await db.commit()
    return True


def _parse_published(entry: dict) -> tuple[str, int]:
    """Lấy thời điểm đăng của video. Trả về (ISO string, unix timestamp).

    yt-dlp trả `timestamp` (chính xác tới giây) cho TikTok và `upload_date`
    (chỉ có ngày) cho YouTube — ưu tiên cái nào chính xác hơn.
    """
    ts = entry.get("timestamp") or entry.get("release_timestamp")
    if ts:
        try:
            return datetime.fromtimestamp(int(ts)).isoformat(), int(ts)
        except (ValueError, OSError, OverflowError):
            pass

    upload_date = entry.get("upload_date") or ""
    if len(upload_date) == 8:
        try:
            dt = datetime.strptime(upload_date, "%Y%m%d")
            return dt.isoformat(), int(dt.timestamp())
        except (ValueError, OSError, OverflowError):
            pass

    return "", 0


def _engagement_rate(views: int, likes: int, comments: int, shares: int) -> float:
    """Tỉ lệ tương tác (%) — dùng để xếp hạng video nào đáng reup."""
    if not views:
        return 0.0
    return round((likes + comments + shares) / views * 100, 2)


def _extract_video_info(url: str) -> dict | None:
    """Lấy thông tin một video đơn lẻ bằng yt-dlp. Trả None nếu không đọc được."""
    import yt_dlp

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "no_color": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        },
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        log.warning("Không đọc được video %s: %s", url, e)
        return None


async def add_videos_by_url(channel_id: int, urls: list[str]) -> dict:
    """Thêm video vào kênh bằng link trực tiếp.

    Dùng cho Facebook — nơi không quét được danh sách video của trang người khác,
    nên người dùng tự dán link từng video muốn theo dõi.
    """
    channel = await get_channel(channel_id)
    if not channel:
        return {"error": "Không tìm thấy kênh"}

    db = await get_db()
    added: list[dict] = []
    skipped: list[str] = []
    failed: list[dict] = []

    for raw_url in urls:
        video_url = raw_url.strip()
        if not video_url:
            continue

        cursor = await db.execute(
            "SELECT id FROM spy_videos WHERE video_url = ?", (video_url,)
        )
        if await cursor.fetchone():
            skipped.append(video_url)
            continue

        info = await asyncio.to_thread(_extract_video_info, video_url)
        if not info:
            failed.append({
                "url": video_url,
                "reason": "Không đọc được video. Kiểm tra link có công khai không.",
            })
            continue

        title = info.get("title") or "Không có tiêu đề"
        views = info.get("view_count") or 0
        likes = info.get("like_count") or 0
        comments = info.get("comment_count") or 0
        shares = info.get("repost_count") or 0
        published_at, published_ts = _parse_published(info)

        await db.execute(
            """INSERT INTO spy_videos
                   (channel_id, video_url, video_id, title, description,
                    thumbnail_url, views_count, likes_count, comments_count,
                    shares_count, duration, published_at, published_ts,
                    engagement_rate, prev_views_count, views_delta, likes_delta,
                    is_new, first_seen_at, last_synced_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0,
                       1, datetime('now'), datetime('now'))""",
            (channel_id, video_url, info.get("id", ""), title,
             (info.get("description") or "")[:500], info.get("thumbnail") or "",
             views, likes, comments, shares, info.get("duration") or 0,
             published_at, published_ts,
             _engagement_rate(views, likes, comments, shares)),
        )
        added.append({"title": title, "views_count": views, "video_url": video_url})

    if added:
        total_cursor = await db.execute(
            "SELECT COUNT(*) AS cnt FROM spy_videos WHERE channel_id = ?", (channel_id,)
        )
        stored = (await total_cursor.fetchone())["cnt"]
        await db.execute(
            """UPDATE spy_channels SET videos_count = ?, last_sync_new = ?,
                   last_synced_at = datetime('now') WHERE id = ?""",
            (stored, len(added), channel_id),
        )
    await db.commit()

    return {
        "success": True,
        "added": len(added),
        "skipped": len(skipped),
        "failed": len(failed),
        "added_list": added,
        "failed_list": failed,
    }


async def _refresh_saved_videos(channel_id: int) -> dict:
    """Cập nhật lại chỉ số của những video đã lưu trong kênh.

    Dùng cho nền tảng không quét được danh sách (Facebook): không tìm video mới,
    chỉ đọc lại từng link đã có để biết views tăng bao nhiêu.
    """
    db = await get_db()
    cursor = await db.execute(
        "SELECT id, video_url, views_count, likes_count FROM spy_videos WHERE channel_id = ?",
        (channel_id,),
    )
    rows = await cursor.fetchall()

    if not rows:
        return {
            "success": True, "new_videos": 0, "updated_videos": 0, "total_entries": 0,
            "new_list": [], "top_risers": [], "channel_total_views": 0,
            "manual": True,
            "message": "Kênh chưa có video nào. Bấm '+ Thêm video' và dán link để bắt đầu theo dõi.",
        }

    await db.execute("UPDATE spy_videos SET is_new = 0 WHERE channel_id = ?", (channel_id,))

    updated = 0
    unreachable = 0
    risers: list[dict] = []
    total_views = 0

    for row in rows:
        info = await asyncio.to_thread(_extract_video_info, row["video_url"])
        if not info:
            unreachable += 1
            continue

        views = info.get("view_count") or 0
        likes = info.get("like_count") or 0
        comments = info.get("comment_count") or 0
        shares = info.get("repost_count") or 0
        prev_views = row["views_count"] or 0
        views_delta = views - prev_views
        total_views += views

        await db.execute(
            """UPDATE spy_videos SET
                   title = ?, thumbnail_url = ?, views_count = ?, likes_count = ?,
                   comments_count = ?, shares_count = ?, engagement_rate = ?,
                   prev_views_count = ?, views_delta = ?, likes_delta = ?,
                   last_synced_at = datetime('now')
               WHERE id = ?""",
            (info.get("title") or "", info.get("thumbnail") or "", views, likes,
             comments, shares, _engagement_rate(views, likes, comments, shares),
             prev_views, views_delta, likes - (row["likes_count"] or 0), row["id"]),
        )
        updated += 1

        if views_delta > 0:
            risers.append({
                "title": info.get("title") or "", "video_url": row["video_url"],
                "views_count": views, "views_delta": views_delta,
                "thumbnail_url": info.get("thumbnail") or "",
            })

    await db.execute(
        """UPDATE spy_channels SET total_views = ?, last_sync_new = 0,
               last_synced_at = datetime('now') WHERE id = ?""",
        (total_views, channel_id),
    )
    await db.commit()

    risers.sort(key=lambda r: r["views_delta"], reverse=True)
    message = f"Đã cập nhật chỉ số {updated} video."
    if unreachable:
        message += f" {unreachable} video không đọc được (có thể đã bị ẩn hoặc xoá)."

    return {
        "success": True,
        "new_videos": 0,
        "updated_videos": updated,
        "total_entries": len(rows),
        "new_list": [],
        "top_risers": risers[:5],
        "channel_total_views": total_views,
        "manual": True,
        "message": message,
    }


async def sync_channel_videos(channel_id: int, max_videos: int = 30) -> dict:
    """Quét video mới nhất của kênh và ghi lại mức tăng trưởng so với lần sync trước."""
    import yt_dlp

    channel = await get_channel(channel_id)
    if not channel:
        return {"error": "Channel not found"}

    # Facebook không cho quét danh sách video của trang người khác -> chỉ làm mới
    # chỉ số của các link đã lưu.
    if channel["platform"] in MANUAL_PLATFORMS:
        return await _refresh_saved_videos(channel_id)

    url = channel["channel_url"]

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "playlistend": max_videos,
        "ignoreerrors": True,
        "no_color": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        },
    }

    try:
        log.info(f"Syncing channel: {url} (max {max_videos} videos)")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            return {"error": "Không thể lấy thông tin kênh"}

        db = await get_db()
        entries = info.get("entries", [])
        if not entries and info.get("id"):
            entries = [info]
        entries = [e for e in entries if e]

        # Đánh dấu lại: cờ "mới" chỉ áp cho lần sync hiện tại
        await db.execute("UPDATE spy_videos SET is_new = 0 WHERE channel_id = ?", (channel_id,))

        new_count = 0
        updated_count = 0
        new_videos: list[dict] = []
        risers: list[dict] = []
        channel_total_views = 0

        for entry in entries:
            video_url = entry.get("webpage_url", entry.get("url", ""))
            if not video_url:
                continue

            title = entry.get("title", "")
            description = (entry.get("description") or "")[:500]
            thumbnail = entry.get("thumbnail", "")
            views = entry.get("view_count", 0) or 0
            likes = entry.get("like_count", 0) or 0
            comments = entry.get("comment_count", 0) or 0
            shares = entry.get("repost_count", 0) or 0
            duration = entry.get("duration", 0) or 0
            published_at, published_ts = _parse_published(entry)
            engagement = _engagement_rate(views, likes, comments, shares)
            channel_total_views += views

            cursor = await db.execute(
                """SELECT id, views_count, likes_count FROM spy_videos
                   WHERE video_url = ?""",
                (video_url,),
            )
            existing = await cursor.fetchone()

            if existing:
                prev_views = existing["views_count"] or 0
                prev_likes = existing["likes_count"] or 0
                views_delta = views - prev_views
                likes_delta = likes - prev_likes

                await db.execute(
                    """UPDATE spy_videos SET
                           title = ?, description = ?, thumbnail_url = ?,
                           views_count = ?, likes_count = ?, comments_count = ?,
                           shares_count = ?, duration = ?, engagement_rate = ?,
                           prev_views_count = ?, views_delta = ?, likes_delta = ?,
                           published_at = COALESCE(NULLIF(?, ''), published_at),
                           published_ts = CASE WHEN ? > 0 THEN ? ELSE published_ts END,
                           last_synced_at = datetime('now'), is_new = 0
                       WHERE id = ?""",
                    (title, description, thumbnail, views, likes, comments, shares,
                     duration, engagement, prev_views, views_delta, likes_delta,
                     published_at, published_ts, published_ts, existing["id"]),
                )
                updated_count += 1

                if views_delta > 0:
                    risers.append({
                        "title": title, "video_url": video_url,
                        "views_count": views, "views_delta": views_delta,
                        "thumbnail_url": thumbnail,
                    })
            else:
                await db.execute(
                    """INSERT INTO spy_videos
                           (channel_id, video_url, video_id, title, description,
                            thumbnail_url, views_count, likes_count, comments_count,
                            shares_count, duration, published_at, published_ts,
                            engagement_rate, prev_views_count, views_delta, likes_delta,
                            is_new, first_seen_at, last_synced_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0,
                               1, datetime('now'), datetime('now'))""",
                    (channel_id, video_url, entry.get("id", ""), title, description,
                     thumbnail, views, likes, comments, shares, duration,
                     published_at, published_ts, engagement),
                )
                new_count += 1
                new_videos.append({
                    "title": title, "video_url": video_url,
                    "views_count": views, "likes_count": likes,
                    "thumbnail_url": thumbnail, "published_at": published_at,
                })

        # Cập nhật thông tin kênh
        channel_name = info.get("channel") or info.get("uploader") or channel["channel_name"]
        avatar = info.get("thumbnail") or ""
        if not avatar and info.get("thumbnails"):
            avatar = (info["thumbnails"][0] or {}).get("url", "")
        followers = info.get("channel_follower_count", 0) or 0

        total_cursor = await db.execute(
            "SELECT COUNT(*) AS cnt FROM spy_videos WHERE channel_id = ?", (channel_id,)
        )
        stored_total = (await total_cursor.fetchone())["cnt"]

        await db.execute(
            """UPDATE spy_channels SET
                   channel_name = ?, avatar_url = ?, followers_count = ?,
                   videos_count = ?, total_views = ?, last_sync_new = ?,
                   last_synced_at = datetime('now')
               WHERE id = ?""",
            (channel_name, avatar, followers, stored_total, channel_total_views,
             new_count, channel_id),
        )
        await db.commit()

        risers.sort(key=lambda r: r["views_delta"], reverse=True)
        new_videos.sort(key=lambda v: v["views_count"], reverse=True)

        log.info("Channel %s sync: %s mới, %s cập nhật", channel_id, new_count, updated_count)

        return {
            "success": True,
            "new_videos": new_count,
            "updated_videos": updated_count,
            "total_entries": len(entries),
            "new_list": new_videos[:10],
            "top_risers": risers[:5],
            "channel_total_views": channel_total_views,
        }

    except Exception as e:
        log.error(f"Sync channel {channel_id} failed: {e}")
        return {"error": str(e)}


# Ánh xạ tiêu chí sắp xếp -> biểu thức SQL.
# "Mới nhất" phải dựa vào published_ts, và lùi về created_at khi nền tảng
# không trả ngày đăng — nếu không, sắp xếp theo chuỗi rỗng sẽ ra thứ tự lộn xộn.
_SORT_EXPRESSIONS = {
    "views_count": "views_count",
    "likes_count": "likes_count",
    "comments_count": "comments_count",
    "duration": "duration",
    "engagement_rate": "engagement_rate",
    "views_delta": "views_delta",
    "published_at": "CASE WHEN published_ts > 0 THEN published_ts "
                    "ELSE strftime('%s', created_at) END",
    "created_at": "strftime('%s', created_at)",
}


async def auto_sync_all_channels() -> dict:
    """Chạy nền: cập nhật chỉ số toàn bộ kênh đang theo dõi.

    TikTok/YouTube sẽ tìm được video mới; Facebook chỉ làm mới chỉ số của các link
    người dùng đã dán (Facebook không cho quét danh sách trang người khác).
    Video nào tăng vọt sẽ được báo qua Telegram để khỏi phải mở tool canh.
    """
    from backend.database import get_setting

    if (await get_setting("spy_auto_sync_enabled", "true")).lower() != "true":
        return {"skipped": True, "reason": "Tự động cập nhật đang tắt"}

    channels = await list_channels("active")
    if not channels:
        return {"channels": 0, "new_videos": 0, "risers": 0}

    try:
        alert_threshold = int(await get_setting("spy_alert_views_delta", "5000"))
    except ValueError:
        alert_threshold = 5000

    total_new = 0
    hot: list[dict] = []
    errors: list[str] = []

    for ch in channels:
        try:
            result = await sync_channel_videos(ch["id"], max_videos=30)
        except Exception as e:
            log.error("Tự động sync kênh %s lỗi: %s", ch["id"], e)
            errors.append(ch["channel_name"])
            continue

        if result.get("error"):
            errors.append(ch["channel_name"])
            continue

        total_new += result.get("new_videos", 0)

        for v in (result.get("top_risers") or []):
            if v.get("views_delta", 0) >= alert_threshold:
                hot.append({**v, "channel_name": ch["channel_name"]})
        for v in (result.get("new_list") or []):
            if v.get("views_count", 0) >= alert_threshold:
                hot.append({**v, "channel_name": ch["channel_name"], "is_new": True})

    if hot:
        await _alert_hot_competitor_videos(hot, alert_threshold)

    log.info(
        "Spy tự động: %s kênh, %s video mới, %s video đáng chú ý%s",
        len(channels), total_new, len(hot),
        f", {len(errors)} kênh lỗi" if errors else "",
    )
    return {
        "channels": len(channels),
        "new_videos": total_new,
        "risers": len(hot),
        "errors": errors,
    }


async def _alert_hot_competitor_videos(videos: list[dict], threshold: int) -> None:
    """Nhắn Telegram khi video đối thủ tăng mạnh hoặc vừa đăng đã nhiều views."""
    from backend.services.telegram import _send_message

    videos.sort(key=lambda v: v.get("views_delta") or v.get("views_count", 0), reverse=True)
    top = videos[:5]

    lines = [f"🔥 <b>Đối thủ đang lên</b> (ngưỡng {threshold:,} views)", ""]
    for v in top:
        title = (v.get("title") or "Không có tiêu đề")[:70]
        if v.get("is_new"):
            detail = f"video mới — {v.get('views_count', 0):,} views"
        else:
            detail = f"▲ {v.get('views_delta', 0):,} views (tổng {v.get('views_count', 0):,})"
        lines.append(f"• <b>{v.get('channel_name', '')}</b>: {detail}")
        lines.append(f"  {title}")
        if v.get("video_url"):
            lines.append(f"  {v['video_url']}")
        lines.append("")

    if len(videos) > len(top):
        lines.append(f"...và {len(videos) - len(top)} video khác.")

    try:
        await _send_message("\n".join(lines))
    except Exception as e:
        log.warning("Không gửi được cảnh báo Spy qua Telegram: %s", e)


async def get_channel_videos(
    channel_id: int,
    sort_by: str = "published_at",
    order: str = "desc",
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Lấy video của kênh kèm thống kê tổng hợp."""
    db = await get_db()

    sort_expr = _SORT_EXPRESSIONS.get(sort_by) or _SORT_EXPRESSIONS["published_at"]
    order_dir = "DESC" if order == "desc" else "ASC"

    stats_cursor = await db.execute(
        """SELECT COUNT(*) AS total,
                  COALESCE(SUM(views_count), 0) AS total_views,
                  COALESCE(SUM(likes_count), 0) AS total_likes,
                  COALESCE(AVG(views_count), 0) AS avg_views,
                  COALESCE(MAX(views_count), 0) AS max_views,
                  COALESCE(SUM(views_delta), 0) AS views_delta,
                  COALESCE(SUM(is_new), 0) AS new_count,
                  COALESCE(SUM(reupped), 0) AS reupped_count,
                  COALESCE(AVG(engagement_rate), 0) AS avg_engagement
           FROM spy_videos WHERE channel_id = ?""",
        (channel_id,),
    )
    stats = dict(await stats_cursor.fetchone())
    stats["avg_views"] = round(stats["avg_views"])
    stats["avg_engagement"] = round(stats["avg_engagement"], 2)

    cursor = await db.execute(
        f"""SELECT * FROM spy_videos
            WHERE channel_id = ?
            ORDER BY {sort_expr} {order_dir}, id DESC
            LIMIT ? OFFSET ?""",
        (channel_id, limit, offset),
    )
    videos = [dict(r) for r in await cursor.fetchall()]

    # Đánh dấu video vượt trội so với mức trung bình của kênh
    avg = stats["avg_views"] or 0
    for v in videos:
        v["is_outperformer"] = bool(avg and v.get("views_count", 0) >= avg * 2)

    return {"videos": videos, "total": stats["total"], "stats": stats}
