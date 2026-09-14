from __future__ import annotations

import asyncio
import json
import re
import subprocess
from pathlib import Path

from backend.config import config

_FILTER_NAME_RE = re.compile(r"[a-z][a-z0-9_]*")


_FILTER_CACHE: set[str] | None = None


def available_filters() -> set[str]:
    """Tập filter mà bản FFmpeg đang cài thực sự có.

    Mỗi bản build FFmpeg bật một tập filter khác nhau: bản rút gọn hay thiếu
    `drawtext` (cần libfreetype). Khi graph gọi một filter không có, FFmpeg chỉ
    nói cụt lủn "Filter not found" nên phải hỏi trước để báo cho rõ.

    Trả về set rỗng nếu không hỏi được — khi đó cứ chạy như cũ, đừng chặn.
    """
    global _FILTER_CACHE
    if _FILTER_CACHE is not None:
        return _FILTER_CACHE

    try:
        out = subprocess.run(
            [config.ffmpeg_path, "-hide_banner", "-filters"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30,
        ).stdout.decode(errors="replace")
    except (OSError, subprocess.SubprocessError):
        return set()

    names: set[str] = set()
    for line in out.splitlines():
        parts = line.split()
        # Cột cờ đứng đầu: 2 ký tự ở FFmpeg 7-8 ("T.", ".S"), 3 ở bản cũ ("TSC")
        if (len(parts) >= 3
                and 1 <= len(parts[0]) <= 3
                and set(parts[0]) <= set("TSC.")
                and _FILTER_NAME_RE.fullmatch(parts[1])):
            names.add(parts[1])

    _FILTER_CACHE = names or None
    return names


async def run_ffmpeg(args: list[str], progress_callback=None) -> subprocess.CompletedProcess:
    cmd = [config.ffmpeg_path, "-y", "-hide_banner", "-loglevel", "info"] + args
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, lambda: subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=600,
    ))
    result.stdout = result.stdout.decode(errors="replace") if isinstance(result.stdout, bytes) else result.stdout
    result.stderr = result.stderr.decode(errors="replace") if isinstance(result.stderr, bytes) else result.stderr
    return result


async def get_video_info(filepath: str | Path) -> dict:
    cmd = [
        config.ffprobe_path,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(filepath),
    ]
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, lambda: subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    ))
    stdout = result.stdout.decode(errors="replace") if isinstance(result.stdout, bytes) else result.stdout

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return {"duration": 0, "width": 0, "height": 0, "filesize": 0, "codec": "", "fps": 30, "bitrate": 0}

    video_stream = None
    for s in data.get("streams", []):
        if s.get("codec_type") == "video":
            video_stream = s
            break

    fmt = data.get("format", {})

    return {
        "duration": float(fmt.get("duration", 0)),
        "width": int(video_stream.get("width", 0)) if video_stream else 0,
        "height": int(video_stream.get("height", 0)) if video_stream else 0,
        "filesize": int(fmt.get("size", 0)),
        "codec": video_stream.get("codec_name", "") if video_stream else "",
        "fps": _parse_fps(video_stream.get("r_frame_rate", "30/1")) if video_stream else 30,
        "bitrate": int(fmt.get("bit_rate", 0)),
    }


def _parse_fps(fps_str: str) -> float:
    try:
        if "/" in fps_str:
            num, den = fps_str.split("/")
            return round(int(num) / int(den), 2)
        return float(fps_str)
    except (ValueError, ZeroDivisionError):
        return 30.0


async def extract_frame(video_path: str | Path, time_sec: float, output_path: str | Path) -> bool:
    result = await run_ffmpeg([
        "-ss", str(time_sec),
        "-i", str(video_path),
        "-vframes", "1",
        "-q:v", "2",
        str(output_path),
    ])
    return result.returncode == 0
