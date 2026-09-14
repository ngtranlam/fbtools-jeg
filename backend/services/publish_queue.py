"""Hàng đợi đăng bài tuần tự.

Trước đây đăng lên nhiều Fanpage là một vòng lặp bắn liên tiếp, bài nọ nối bài
kia không nghỉ. Với Facebook đó là dấu hiệu máy chạy tự động rõ rệt nhất: hàng
chục Page cùng đăng một video trong vài giây.

Module này xếp mọi bài vào MỘT hàng đợi chung và một luồng chạy duy nhất lấy ra
từng bài một. Đăng xong một bài, nghỉ ngẫu nhiên 60–120 giây rồi mới sang bài
sau. Vì hàng đợi là chung cho cả tiến trình nên dù Content Studio, Video Studio
hay bộ hẹn giờ cùng đẩy bài vào, chúng vẫn nối đuôi nhau chứ không bắn song song.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from collections import deque
from datetime import datetime

from backend.database import get_db
from backend.utils.websocket import ws_manager

log = logging.getLogger(__name__)

#: Khoảng nghỉ giữa hai bài liên tiếp, tính bằng giây.
DELAY_MIN = 60
DELAY_MAX = 120

#: Nghỉ trước khi thả bình luận đầu tiên, để không dính ngay sau bài đăng.
COMMENT_DELAY_MIN = 10
COMMENT_DELAY_MAX = 60

_queue: deque[dict] = deque()
_worker: asyncio.Task | None = None
_current: dict | None = None
_wait_until: float = 0.0
_lock = asyncio.Lock()

#: Vài bài gần nhất đã xử lý xong — để giao diện hiện lịch sử ngắn
_recent: deque[dict] = deque(maxlen=30)


def _delay_range() -> tuple[int, int]:
    """Khoảng nghỉ, cho phép chỉnh trong Cài đặt nhưng không được về 0."""
    try:
        from backend.config import config
        lo = int(getattr(config, "publish_delay_min", DELAY_MIN) or DELAY_MIN)
        hi = int(getattr(config, "publish_delay_max", DELAY_MAX) or DELAY_MAX)
    except Exception:
        lo, hi = DELAY_MIN, DELAY_MAX
    lo = max(5, lo)
    hi = max(lo, hi)
    return lo, hi


def status() -> dict:
    """Tình trạng hàng đợi để giao diện hiển thị."""
    con_lai = 0.0
    if _wait_until:
        try:
            con_lai = max(0.0, _wait_until - asyncio.get_running_loop().time())
        except RuntimeError:
            con_lai = 0.0
    return {
        "running": bool(_worker and not _worker.done()),
        "waiting": len(_queue),
        "current": _current,
        "next_in": round(con_lai),
        "recent": list(_recent),
        "delay_min": _delay_range()[0],
        "delay_max": _delay_range()[1],
    }


async def enqueue(item: dict) -> int:
    """Đưa một bài vào cuối hàng đợi. Trả về vị trí (1 = đăng ngay)."""
    _queue.append(item)
    await _ensure_worker()
    vitri = len(_queue) + (1 if _current else 0)
    await _broadcast("queued", {"item": _describe(item), "position": vitri})
    return vitri


async def cancel_all() -> int:
    """Bỏ mọi bài còn chờ. Bài đang đăng dở thì vẫn để chạy nốt."""
    bo = len(_queue)
    huy = list(_queue)
    _queue.clear()

    db = await get_db()
    for it in huy:
        if it.get("post_id"):
            await db.execute(
                "UPDATE posts SET status = 'failed', error_message = ? WHERE id = ?",
                ("Đã huỷ khỏi hàng đợi", it["post_id"]),
            )
    await db.commit()
    await _broadcast("cancelled", {"removed": bo})
    return bo


def _describe(item: dict) -> dict:
    return {
        "post_id": item.get("post_id"),
        "platform": item.get("platform", "facebook"),
        "target_id": item.get("target_id"),
        "target_name": item.get("target_name", ""),
    }


async def _broadcast(event: str, extra: dict | None = None) -> None:
    try:
        await ws_manager.broadcast({
            "type": "publish_queue",
            "event": event,
            **status(),
            **(extra or {}),
        })
    except Exception as e:
        log.debug("Không gửi được tin hàng đợi: %s", e)


async def _ensure_worker() -> None:
    global _worker
    async with _lock:
        if _worker is None or _worker.done():
            _worker = asyncio.create_task(_run())


async def _run() -> None:
    """Luồng duy nhất xử lý hàng đợi, mỗi lần đúng một bài."""
    global _current, _wait_until
    try:
        while _queue:
            _current = _describe(_queue[0])
            item = _queue.popleft()
            await _broadcast("publishing")

            ket_qua = await _publish_one(item)
            _recent.appendleft({
                **_describe(item),
                "status": ket_qua["status"],
                "error": ket_qua.get("error", ""),
                "at": datetime.now().strftime("%H:%M:%S"),
            })
            _current = None
            await _broadcast("done", {"result": ket_qua})

            # Nghỉ trước bài kế tiếp. Bài cuối thì thôi, không bắt chờ vô ích.
            if _queue:
                lo, hi = _delay_range()
                nghi = random.randint(lo, hi)
                log.info("Hàng đợi: nghỉ %ss trước bài kế tiếp (còn %s bài)",
                         nghi, len(_queue))
                loop = asyncio.get_running_loop()
                _wait_until = loop.time() + nghi
                # Đếm ngược từng giây để giao diện thấy, và để huỷ có tác dụng ngay
                while loop.time() < _wait_until and _queue:
                    await asyncio.sleep(1)
                    if int(loop.time() - (_wait_until - nghi)) % 5 == 0:
                        await _broadcast("waiting")
                _wait_until = 0.0
    except asyncio.CancelledError:
        raise
    except Exception as e:
        log.error("Hàng đợi đăng bài lỗi: %s", e, exc_info=True)
    finally:
        _current = None
        _wait_until = 0.0
        await _broadcast("idle")


async def _publish_one(item: dict) -> dict:
    """Đăng đúng một bài rồi ghi kết quả vào DB."""
    from backend.services.publisher import publish_to_platform

    platform = item.get("platform", "facebook")
    target_id = item.get("target_id")
    post_id = item.get("post_id")
    db = await get_db()

    try:
        pub = await publish_to_platform(
            platform=platform,
            target_id=target_id,
            filepath=item["filepath"],
            caption=item.get("caption", ""),
            **(item.get("extra") or {}),
        )
        platform_post_id = pub.get("platform_post_id", "")
        fb_post_id = pub.get("fb_post_id", "") or platform_post_id

        if post_id:
            await db.execute(
                """UPDATE posts SET status = 'posted', fb_post_id = ?,
                       platform_post_id = ?, posted_at = datetime('now'),
                       error_message = ''
                   WHERE id = ?""",
                (fb_post_id, platform_post_id, post_id),
            )
            await db.commit()

        if item.get("first_comment") and fb_post_id and platform == "facebook":
            asyncio.create_task(_first_comment(
                target_id, fb_post_id, item["first_comment"],
                item.get("comment_image_url") or "", post_id,
            ))

        return {"status": "posted", "post_id": post_id,
                "platform_post_id": platform_post_id}

    except Exception as e:
        log.error("Đăng bài thất bại (%s/%s): %s", platform, target_id, e)
        if post_id:
            await db.execute(
                "UPDATE posts SET status = 'failed', error_message = ? WHERE id = ?",
                (str(e), post_id),
            )
            await db.commit()
        return {"status": "failed", "post_id": post_id, "error": str(e)}


async def _first_comment(target_id, fb_post_id, message, image_url, post_id) -> None:
    """Thả bình luận đầu tiên sau khi bài đã lên."""
    from backend.services.facebook import post_comment
    try:
        await asyncio.sleep(random.randint(COMMENT_DELAY_MIN, COMMENT_DELAY_MAX))
        await post_comment(target_id, fb_post_id, message, attachment_url=image_url)
        if post_id:
            db = await get_db()
            await db.execute(
                "UPDATE posts SET comment_status = 'sent' WHERE id = ?", (post_id,))
            await db.commit()
        log.info("Đã thả bình luận đầu cho bài %s", post_id)
    except Exception as e:
        log.error("Bình luận đầu thất bại: %s", e)


async def queue_post(
    *, platform: str, target_id, filepath: str, caption: str,
    variant_id=None, extra: dict | None = None, first_comment: str = "",
    comment_image_url: str = "", target_name: str = "",
) -> dict:
    """Ghi bài vào DB với trạng thái `queued` rồi xếp vào hàng đợi."""
    db = await get_db()
    page_id = target_id if platform == "facebook" else None
    channel_id = target_id if platform != "facebook" else None

    cursor = await db.execute(
        """INSERT INTO posts (page_id, channel_id, platform, variant_id, caption,
               filepath, first_comment, comment_image_url, extra_data, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued')""",
        (page_id, channel_id, platform, variant_id, caption, filepath,
         first_comment or "", comment_image_url or "",
         json.dumps(extra or {}, ensure_ascii=False)),
    )
    await db.commit()
    post_id = cursor.lastrowid

    vitri = await enqueue({
        "post_id": post_id,
        "platform": platform,
        "target_id": target_id,
        "target_name": target_name,
        "filepath": filepath,
        "caption": caption,
        "extra": extra or {},
        "first_comment": first_comment or "",
        "comment_image_url": comment_image_url or "",
    })
    return {"post_id": post_id, "position": vitri}
