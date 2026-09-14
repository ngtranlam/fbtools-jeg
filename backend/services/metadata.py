from __future__ import annotations

import json
from pathlib import Path

from backend.models import VideoMetadata
from backend.utils.ffmpeg import run_ffmpeg, get_video_info


async def read_metadata(filepath: str) -> VideoMetadata:
    info = await get_video_info(filepath)
    return VideoMetadata(
        title=info.get("title", ""),
        duration=info.get("duration", 0),
    )


async def write_metadata(filepath: str, metadata: VideoMetadata) -> bool:
    fp = Path(filepath)
    temp_path = fp.parent / f"_meta_{fp.name}"

    args = ["-i", str(fp)]

    if metadata.title:
        args.extend(["-metadata", f"title={metadata.title}"])
    if metadata.description:
        args.extend(["-metadata", f"comment={metadata.description}"])
    if metadata.author:
        args.extend(["-metadata", f"artist={metadata.author}"])
    if metadata.creation_date:
        args.extend(["-metadata", f"date={metadata.creation_date}"])
    if metadata.tags:
        args.extend(["-metadata", f"genre={','.join(metadata.tags)}"])

    args.extend(["-c", "copy", str(temp_path)])

    result = await run_ffmpeg(args)

    if result.returncode == 0 and temp_path.exists():
        fp.unlink()
        temp_path.rename(fp)
        return True

    temp_path.unlink(missing_ok=True)
    return False


async def strip_metadata(filepath: str) -> bool:
    fp = Path(filepath)
    temp_path = fp.parent / f"_strip_{fp.name}"

    result = await run_ffmpeg([
        "-i", str(fp),
        "-map_metadata", "-1",
        "-fflags", "+bitexact",
        "-c", "copy",
        str(temp_path),
    ])

    if result.returncode == 0 and temp_path.exists():
        fp.unlink()
        temp_path.rename(fp)
        return True

    temp_path.unlink(missing_ok=True)
    return False
