from __future__ import annotations

import re
import uuid
import shutil
import asyncio
from pathlib import Path

import yt_dlp

from backend.config import DOWNLOADS_DIR
from backend.models import VideoInfo, Platform
from backend.utils.ffmpeg import get_video_info
from backend.utils.websocket import ws_manager


_PLATFORM_PATTERNS = {
    Platform.YOUTUBE: [r"youtube\.com", r"youtu\.be"],
    Platform.TIKTOK: [r"tiktok\.com", r"vm\.tiktok"],
    Platform.FACEBOOK: [r"facebook\.com", r"fb\.watch", r"fb\.com"],
    Platform.INSTAGRAM: [r"instagram\.com"],

}


def detect_platform(url: str) -> Platform:
    for platform, patterns in _PLATFORM_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, url, re.IGNORECASE):
                return platform
    return Platform.UNKNOWN


_videos_db: dict[str, VideoInfo] = {}


def get_all_videos() -> list[VideoInfo]:
    _sync_from_disk()
    return list(_videos_db.values())


def get_video(video_id: str) -> VideoInfo | None:
    return _videos_db.get(video_id)


def _sync_from_disk():
    existing_files = set()
    for f in DOWNLOADS_DIR.glob("*.mp4"):
        existing_files.add(f.name)
    for f in DOWNLOADS_DIR.glob("*.webm"):
        existing_files.add(f.name)
    for f in DOWNLOADS_DIR.glob("*.mkv"):
        existing_files.add(f.name)

    to_remove = [
        vid for vid, info in _videos_db.items()
        if info.filename not in existing_files
    ]
    for vid in to_remove:
        del _videos_db[vid]


async def download_video(url: str) -> VideoInfo:
    video_id = uuid.uuid4().hex[:12]
    platform = detect_platform(url)

    await ws_manager.broadcast({
        "type": "download_progress",
        "video_id": video_id,
        "status": "starting",
        "progress": 0,
        "message": f"Starting download from {platform.value}...",
    })

    output_template = str(DOWNLOADS_DIR / f"{video_id}_%(title).50s.%(ext)s")

    # Capture running loop BEFORE entering executor thread
    loop = asyncio.get_running_loop()

    def progress_hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            pct = (downloaded / total * 100) if total > 0 else 0
            speed = d.get("speed", 0) or 0
            speed_str = f"{speed / 1024 / 1024:.1f} MB/s" if speed else "..."
            loop.call_soon_threadsafe(
                asyncio.ensure_future,
                ws_manager.broadcast({
                    "type": "download_progress",
                    "video_id": video_id,
                    "status": "downloading",
                    "progress": round(pct, 1),
                    "message": f"Downloading... {pct:.1f}% ({speed_str})",
                })
            )
        elif d["status"] == "finished":
            loop.call_soon_threadsafe(
                asyncio.ensure_future,
                ws_manager.broadcast({
                    "type": "download_progress",
                    "video_id": video_id,
                    "status": "processing",
                    "progress": 95,
                    "message": "Processing downloaded file...",
                })
            )

    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": output_template,
        "progress_hooks": [progress_hook],
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        },
        "extractor_args": {"tiktok": {"api_hostname": ["api22-normal-c-alisg.tiktokv.com"]}},
        "socket_timeout": 30,
    }

    info_dict = await loop.run_in_executor(None, lambda: _run_download(ydl_opts, url))

    downloaded_file = _find_downloaded_file(video_id)
    if not downloaded_file:
        raise FileNotFoundError(f"Download completed but file not found for {video_id}")

    try:
        probe = await get_video_info(downloaded_file)
    except (FileNotFoundError, OSError):
        probe = {"duration": 0, "width": 0, "height": 0, "filesize": 0, "bitrate": 0}

    video = VideoInfo(
        id=video_id,
        title=info_dict.get("title", downloaded_file.stem),
        description=info_dict.get("description", ""),
        filename=downloaded_file.name,
        filepath=str(downloaded_file),
        platform=platform,
        duration=probe.get("duration", 0),
        width=probe.get("width", 0),
        height=probe.get("height", 0),
        filesize=downloaded_file.stat().st_size,
        thumbnail=info_dict.get("thumbnail", ""),
    )

    _videos_db[video_id] = video

    await ws_manager.broadcast({
        "type": "download_progress",
        "video_id": video_id,
        "status": "completed",
        "progress": 100,
        "message": "Download complete!",
        "video": video.model_dump(),
    })

    return video


async def add_uploaded_video(filepath: Path, original_filename: str) -> VideoInfo:
    video_id = uuid.uuid4().hex[:12]
    ext = filepath.suffix or ".mp4"
    safe_name = re.sub(r'[^\w\-.]', '_', original_filename)
    new_name = f"{video_id}_{safe_name}"
    if not new_name.endswith(ext):
        new_name += ext

    dest = DOWNLOADS_DIR / new_name
    shutil.move(str(filepath), str(dest))

    try:
        probe = await get_video_info(dest)
    except (FileNotFoundError, OSError):
        probe = {"duration": 0, "width": 0, "height": 0, "filesize": 0, "bitrate": 0}

    video = VideoInfo(
        id=video_id,
        title=Path(original_filename).stem,
        filename=dest.name,
        filepath=str(dest),
        platform=Platform.UNKNOWN,
        duration=probe.get("duration", 0),
        width=probe.get("width", 0),
        height=probe.get("height", 0),
        filesize=dest.stat().st_size,
    )

    _videos_db[video_id] = video
    return video


def delete_video(video_id: str) -> bool:
    video = _videos_db.get(video_id)
    if not video:
        return False
    fp = Path(video.filepath)
    if fp.exists():
        fp.unlink()
    del _videos_db[video_id]
    return True


def _run_download(opts: dict, url: str) -> dict:
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info or {}


def _find_downloaded_file(video_id: str) -> Path | None:
    for ext in ["mp4", "webm", "mkv", "avi", "mov"]:
        for f in DOWNLOADS_DIR.glob(f"{video_id}_*.{ext}"):
            return f
    for f in DOWNLOADS_DIR.glob(f"{video_id}*"):
        if f.is_file():
            return f
    return None
