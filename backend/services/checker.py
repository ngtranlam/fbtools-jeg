from __future__ import annotations

import uuid
import logging
from pathlib import Path

import imagehash
from PIL import Image

from backend.config import TEMP_DIR, REPORTS_DIR, VARIANTS_DIR
from backend.models import (
    CheckRequest, UniquenessReport, VideoHashResult, FrameHash,
)
from backend.utils.ffmpeg import extract_frame, get_video_info

logger = logging.getLogger(__name__)

# Sample at more positions for better accuracy
SAMPLE_POSITIONS = [0.0, 0.15, 0.30, 0.50, 0.70, 0.85, 1.0]

# pHash distance threshold — higher = more tolerant of differences
# Values below this are considered "same"
# Typical distances: identical=0, minor edit=5-10, crop+color=12-18, heavy transform=20+
HASH_DISTANCE_THRESHOLD = 8

# Percentage of frames that must be similar to flag as duplicate
SIMILARITY_RATIO_THRESHOLD = 0.7


def _compute_multi_hash(img: Image.Image) -> dict[str, imagehash.ImageHash]:
    """Compute multiple hash types for more robust comparison."""
    return {
        "phash": imagehash.phash(img, hash_size=16),       # 16x16 for higher resolution
        "dhash": imagehash.dhash(img, hash_size=16),        # difference hash
        "whash": imagehash.whash(img, hash_size=16),        # wavelet hash
    }


def _compute_distance(hashes_a: dict, hashes_b: dict) -> float:
    """Weighted average distance across hash types."""
    weights = {"phash": 0.4, "dhash": 0.35, "whash": 0.25}
    total = 0.0
    for key, weight in weights.items():
        if key in hashes_a and key in hashes_b:
            dist = hashes_a[key] - hashes_b[key]
            # Normalize to 0-1 range (max distance for 16x16 = 256)
            normalized = dist / 256.0
            total += normalized * weight
    # Return as a percentage distance (0 = identical, 100 = completely different)
    return total * 100


async def check_uniqueness(video_paths: list[str]) -> UniquenessReport:
    report_id = uuid.uuid4().hex[:12]
    results: list[VideoHashResult] = []
    all_hashes: dict[str, list[dict]] = {}  # video_stem -> list of multi-hashes

    for vpath in video_paths:
        fp = Path(vpath)
        if not fp.exists():
            logger.warning(f"Video not found: {vpath}")
            continue

        probe = await get_video_info(fp)
        duration = probe.get("duration", 0)

        vid_result = VideoHashResult(
            video_id=fp.stem,
            filename=fp.name,
        )

        video_hashes = []

        for pos_pct in SAMPLE_POSITIONS:
            time_sec = max(0.01, duration * pos_pct - 0.01) if pos_pct == 1.0 else max(0.01, duration * pos_pct)
            frame_path = TEMP_DIR / f"{report_id}_{fp.stem}_{int(pos_pct*100)}.jpg"

            ok = await extract_frame(fp, time_sec, frame_path)
            if ok and frame_path.exists():
                try:
                    img = Image.open(frame_path)
                    multi_hash = _compute_multi_hash(img)
                    video_hashes.append(multi_hash)

                    # Store phash for display
                    vid_result.frame_hashes.append(FrameHash(
                        position=f"{int(pos_pct*100)}%",
                        hash_value=str(multi_hash["phash"]),
                    ))
                except Exception as e:
                    logger.error(f"Hash error for {fp.name} at {pos_pct}: {e}")
                finally:
                    frame_path.unlink(missing_ok=True)

        all_hashes[fp.stem] = video_hashes
        results.append(vid_result)

    # ── Compare all pairs ──
    duplicate_pairs = []
    stems = list(all_hashes.keys())

    for i in range(len(stems)):
        for j in range(i + 1, len(stems)):
            hashes_a = all_hashes[stems[i]]
            hashes_b = all_hashes[stems[j]]

            if not hashes_a or not hashes_b:
                continue

            similar_frames = 0
            total_compared = 0
            total_distance = 0.0

            for ha, hb in zip(hashes_a, hashes_b):
                distance = _compute_distance(ha, hb)
                total_distance += distance
                total_compared += 1
                # Consider frames "similar" if distance < threshold
                if distance < 3.0:  # 3% distance = very similar
                    similar_frames += 1

            if total_compared == 0:
                continue

            avg_distance = total_distance / total_compared
            similarity_pct = max(0, 100 - avg_distance * 10)  # Scale for display
            similar_ratio = similar_frames / total_compared

            # Flag as duplicate only if BOTH conditions met:
            # 1. Average distance is very low (frames are perceptually similar)
            # 2. Most frames are similar (not just 1-2 coincidences)
            if avg_distance < 5.0 and similar_ratio >= SIMILARITY_RATIO_THRESHOLD:
                duplicate_pairs.append({
                    "video_a": results[i].filename if i < len(results) else stems[i],
                    "video_b": results[j].filename if j < len(results) else stems[j],
                    "similarity": round(similarity_pct, 1),
                    "avg_distance": round(avg_distance, 2),
                })

    # Calculate unique count properly
    flagged_videos = set()
    for pair in duplicate_pairs:
        flagged_videos.add(pair["video_a"])
        flagged_videos.add(pair["video_b"])
    unique_count = len(results) - len(flagged_videos) + (1 if flagged_videos else 0)

    report = UniquenessReport(
        report_id=report_id,
        total_videos=len(results),
        unique_count=max(0, unique_count),
        duplicate_pairs=duplicate_pairs,
        results=results,
        all_unique=len(duplicate_pairs) == 0,
    )

    logger.info(f"Uniqueness check: {len(results)} videos, {len(duplicate_pairs)} duplicate pairs, {unique_count} unique")
    return report


async def check_variants_for_job(job_id: str) -> UniquenessReport:
    variant_dir = VARIANTS_DIR / job_id
    if not variant_dir.exists():
        raise FileNotFoundError(f"Variant directory not found: {job_id}")

    video_paths = [str(f) for f in variant_dir.glob("*.mp4")]
    if not video_paths:
        raise ValueError(f"No variants found in {job_id}")

    return await check_uniqueness(video_paths)
