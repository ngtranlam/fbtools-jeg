from __future__ import annotations

import json
import logging
import random
import uuid
import asyncio
from pathlib import Path

from backend.config import VARIANTS_DIR
from backend.database import get_db
from backend.models import (
    TransformType, SpoofRequest, SpoofJob, VariantInfo, JobStatus,
)
from backend.services.downloader import get_video
from backend.services.transform_profiles import get_profile, DEFAULT_RANGES
from backend.utils.ffmpeg import run_ffmpeg, get_video_info
from backend.utils.websocket import ws_manager

logger = logging.getLogger(__name__)

_jobs: dict[str, SpoofJob] = {}


def get_job(job_id: str) -> SpoofJob | None:
    return _jobs.get(job_id)


def get_all_jobs() -> list[SpoofJob]:
    return list(_jobs.values())


async def create_spoof_job(req: SpoofRequest) -> SpoofJob:
    video = get_video(req.video_id)
    if not video:
        raise ValueError(f"Video {req.video_id} not found")

    job_id = uuid.uuid4().hex[:12]
    job = SpoofJob(
        job_id=job_id,
        video_id=req.video_id,
        video_title=video.title,
        video_description=getattr(video, 'description', ''),
        num_variants=req.num_variants,
        status=JobStatus.PENDING,
    )
    _jobs[job_id] = job

    asyncio.create_task(_run_spoof_job(job, req, video.filepath))
    return job


def _sanitize_filename(name: str, max_len: int = 80) -> str:
    """Sanitize a string for use in filenames."""
    import re as _re
    safe = _re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', name)
    safe = safe.strip('. ')
    if len(safe) > max_len:
        safe = safe[:max_len].rstrip('. ')
    return safe or 'video'


async def _run_spoof_job(job: SpoofJob, req: SpoofRequest, input_path: str):
    from datetime import datetime
    job.status = JobStatus.RUNNING
    job.started_at = datetime.now().isoformat()

    output_dir = VARIANTS_DIR / job.job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build readable filename base from video title
    video = get_video(req.video_id)
    base_name = _sanitize_filename(video.title if video else req.video_id)

    profile = get_profile(req.profile)
    available_transforms = req.transforms or profile["transforms"]
    ranges = {**DEFAULT_RANGES, **profile.get("ranges", {})}

    # Get source video info for smart bitrate calculation
    try:
        source_info = await get_video_info(Path(input_path))
    except (FileNotFoundError, OSError):
        source_info = {}
    source_bitrate = source_info.get("bitrate", 0)  # bits/sec

    try:
        for i in range(req.num_variants):
            variant_id = f"v{i+1}"

            await ws_manager.broadcast({
                "type": "spoof_progress",
                "job_id": job.job_id,
                "status": "processing",
                "current": i + 1,
                "total": req.num_variants,
                "message": f"Creating variant {i+1}/{req.num_variants}...",
            })

            seed = random.SystemRandom().randint(0, 2**32)
            rng = random.Random(seed)

            # Apply ALL transforms from the profile — they're all subtle enough
            chosen = list(available_transforms)
            rng.shuffle(chosen)

            output_file = output_dir / f"{base_name} - {variant_id}.mp4"

            ffmpeg_args = _build_ffmpeg_command(
                input_path, str(output_file), chosen, ranges, rng,
                req.upscale, req.upscale_factor,
                variant_index=i, source_bitrate=source_bitrate,
            )

            logger.info(f"Variant {variant_id} FFmpeg args: ffmpeg {' '.join(ffmpeg_args[:20])}...")
            result = await run_ffmpeg(ffmpeg_args)

            if result.returncode != 0:
                logger.warning(f"Variant {variant_id} failed: {result.stderr[:500]}")
                await ws_manager.broadcast({
                    "type": "spoof_progress",
                    "job_id": job.job_id,
                    "status": "warning",
                    "message": f"Variant {i+1} retrying with simpler transforms...",
                })
                simple_transforms = [
                    TransformType.METADATA_STRIP, TransformType.BRIGHTNESS,
                    TransformType.BITRATE, TransformType.PIXEL_SHIFT,
                ]
                ffmpeg_args = _build_ffmpeg_command(
                    input_path, str(output_file), simple_transforms, ranges, rng,
                    False, 2, variant_index=i, source_bitrate=source_bitrate,
                )
                result = await run_ffmpeg(ffmpeg_args)

            if output_file.exists():
                try:
                    probe = await get_video_info(output_file)
                except (FileNotFoundError, OSError):
                    probe = {"duration": 0, "width": 0, "height": 0}

                # Save variant to DB
                db_id = None
                try:
                    db = await get_db()
                    cursor = await db.execute(
                        """INSERT INTO variants (video_id, filename, filepath, profile, transforms, filesize, duration, width, height, status)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ready')""",
                        (
                            req.video_id,
                            output_file.name,
                            str(output_file),
                            req.profile,
                            json.dumps([t.value for t in chosen]),
                            output_file.stat().st_size,
                            probe.get("duration", 0),
                            probe.get("width", 0),
                            probe.get("height", 0),
                        ),
                    )
                    await db.commit()
                    db_id = cursor.lastrowid
                except Exception as db_err:
                    logger.warning(f"Failed to save variant to DB: {db_err}")

                variant = VariantInfo(
                    id=str(db_id) if db_id else variant_id,
                    filename=output_file.name,
                    filepath=str(output_file),
                    transforms_applied=[t.value for t in chosen],
                    filesize=output_file.stat().st_size,
                    duration=probe.get("duration", 0),
                    width=probe.get("width", 0),
                    height=probe.get("height", 0),
                )
                job.variants.append(variant)
                job.completed_variants = len(job.variants)
            else:
                logger.error(f"Variant {variant_id} output file missing")

        job.status = JobStatus.COMPLETED
        job.finished_at = datetime.now().isoformat()

        await ws_manager.broadcast({
            "type": "spoof_progress",
            "job_id": job.job_id,
            "status": "completed",
            "current": req.num_variants,
            "total": req.num_variants,
            "message": f"All {req.num_variants} variants created!",
            "variants": [v.model_dump() for v in job.variants],
        })

    except Exception as e:
        logger.error(f"Spoof job {job.job_id} failed: {e}", exc_info=True)
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.finished_at = datetime.now().isoformat()
        await ws_manager.broadcast({
            "type": "spoof_progress",
            "job_id": job.job_id,
            "status": "failed",
            "message": f"Error: {e}",
        })


# ── Variant strategies ──
# Each variant gets a DIFFERENT combination of gamma curve + subtle color direction
# This guarantees pixel-level uniqueness while keeping text readable
# NOTE: Mirror/hflip removed — it reverses text, killing viral potential
_VARIANT_STRATEGIES = [
    {"gamma_dir": "bright", "color_dir": "warm"},
    {"gamma_dir": "dark",   "color_dir": "cool"},
    {"gamma_dir": "bright", "color_dir": "vivid"},
    {"gamma_dir": "dark",   "color_dir": "soft"},
    {"gamma_dir": "mid",    "color_dir": "neutral"},
    {"gamma_dir": "dark",   "color_dir": "warm"},
    {"gamma_dir": "bright", "color_dir": "cool"},
    {"gamma_dir": "mid",    "color_dir": "vivid"},
    {"gamma_dir": "dark",   "color_dir": "soft"},
    {"gamma_dir": "mid",    "color_dir": "neutral"},
]


def _get_strategy(variant_index: int) -> dict:
    return _VARIANT_STRATEGIES[variant_index % len(_VARIANT_STRATEGIES)]


def _build_ffmpeg_command(
    input_path: str,
    output_path: str,
    transforms: list[TransformType],
    ranges: dict,
    rng: random.Random,
    upscale: bool,
    upscale_factor: int,
    variant_index: int = 0,
    source_bitrate: int = 0,
) -> list[str]:
    strategy = _get_strategy(variant_index)

    vfilters: list[str] = []
    afilters: list[str] = []
    extra_args: list[str] = []
    input_args: list[str] = ["-i", input_path]

    # ── EQ values (combined into single filter at end) ──
    brightness_val = 0.0
    contrast_val = 1.0
    saturation_val = 1.0

    for t in transforms:
        if t == TransformType.CROP:
            pct = rng.uniform(*ranges.get("crop_pct", (0.005, 0.015)))
            # Tiny directional crop — visually unnoticeable
            left = rng.uniform(0, pct * 0.5)
            top = rng.uniform(0, pct * 0.5)
            w = 1.0 - pct
            h = 1.0 - pct
            vfilters.append(f"crop=iw*{w:.4f}:ih*{h:.4f}:iw*{left:.4f}:ih*{top:.4f}")

        elif t == TransformType.BRIGHTNESS:
            lo, hi = ranges.get("brightness", (-0.02, 0.02))
            if strategy["color_dir"] == "warm":
                brightness_val = rng.uniform(max(0.005, lo), hi)
            elif strategy["color_dir"] == "cool":
                brightness_val = rng.uniform(lo, min(-0.005, hi))
            else:
                brightness_val = rng.uniform(lo, hi)

        elif t == TransformType.CONTRAST:
            lo, hi = ranges.get("contrast", (0.98, 1.02))
            contrast_val = rng.uniform(lo, hi)

        elif t == TransformType.SATURATION:
            lo, hi = ranges.get("saturation", (0.97, 1.03))
            if strategy["color_dir"] == "vivid":
                saturation_val = rng.uniform(max(1.01, lo), hi)
            elif strategy["color_dir"] == "soft":
                saturation_val = rng.uniform(lo, min(0.99, hi))
            else:
                saturation_val = rng.uniform(lo, hi)

        elif t == TransformType.HUE_SHIFT:
            lo, hi = ranges.get("hue_degrees", (-2, 2))
            if strategy["color_dir"] == "warm":
                val = rng.uniform(max(0.3, lo), hi)
            elif strategy["color_dir"] == "cool":
                val = rng.uniform(lo, min(-0.3, hi))
            else:
                val = rng.uniform(lo, hi)
            vfilters.append(f"hue=h={val:.2f}")

        elif t == TransformType.SPEED:
            # ±1% speed — duration difference is imperceptible (~0.25s on 25s video)
            lo, hi = ranges.get("speed_factor", (0.99, 1.01))
            factor = rng.uniform(lo, hi)
            pts = 1.0 / factor
            vfilters.append(f"setpts={pts:.6f}*PTS")
            if 0.5 <= factor <= 2.0:
                afilters.append(f"atempo={factor:.6f}")

        elif t == TransformType.SCALE:
            pct = rng.uniform(*ranges.get("scale_pct", (-2, 2)))
            factor = 1.0 + pct / 100
            vfilters.append(f"scale=iw*{factor:.4f}:ih*{factor:.4f}")

        elif t == TransformType.BITRATE:
            # Use source bitrate to maintain or IMPROVE quality
            factor = rng.uniform(*ranges.get("bitrate_factor", (0.85, 1.15)))
            if source_bitrate > 0:
                base_kbps = source_bitrate // 1000
                bitrate = int(base_kbps * factor)
            else:
                bitrate = int(3000 * factor)
            # Minimum 1500k for decent quality
            bitrate = max(1500, bitrate)
            extra_args.extend(["-b:v", f"{bitrate}k"])

        elif t == TransformType.FRAMERATE:
            fps_options = [29.97, 30, 25, 24, 23.976]
            fps = rng.choice(fps_options)
            extra_args.extend(["-r", str(fps)])

        elif t == TransformType.CODEC:
            presets = ["medium", "slow"]  # slow = better quality
            extra_args.extend(["-c:v", "libx264", "-preset", rng.choice(presets)])

        elif t == TransformType.MIRROR:
            # DISABLED — hflip reverses text in video, ruins viral content
            # Instead, use gamma curve for pixel-level uniqueness
            gamma_dir = strategy.get("gamma_dir", "mid")
            if gamma_dir == "bright":
                gamma_val = rng.uniform(1.02, 1.06)
            elif gamma_dir == "dark":
                gamma_val = rng.uniform(0.94, 0.98)
            else:
                gamma_val = rng.uniform(0.98, 1.02)
            vfilters.append(f"eq=gamma={gamma_val:.4f}")

        elif t == TransformType.NOISE:
            # Very light film grain — adds texture without degradation
            lo, hi = [int(x) for x in ranges.get("noise_strength", (1, 2))]
            strength = rng.randint(lo, hi)
            vfilters.append(f"noise=alls={strength}:allf=t")

        elif t == TransformType.AUDIO_PITCH:
            pct = rng.uniform(*ranges.get("audio_pitch_pct", (-1, 1)))
            rate_factor = 1.0 + pct / 100
            new_rate = int(44100 * rate_factor)
            afilters.append(f"asetrate={new_rate},aresample=44100")

        elif t == TransformType.PIXEL_SHIFT:
            max_shift = ranges.get("pixel_shift_max", 3)
            shift_x = rng.randint(1, max_shift)
            shift_y = rng.randint(1, max_shift)
            # Pixel shift + pad back to original size to avoid dimension shrink
            vfilters.append(f"crop=iw-{shift_x}:ih-{shift_y}:{shift_x}:0,pad=iw+{shift_x}:ih+{shift_y}:0:{shift_y}")

        # NOTE: TRIM and ROTATION are intentionally NOT handled here.
        # TRIM changes duration (user doesn't want that)
        # ROTATION creates black borders (degrades quality)

    # ── Build combined eq filter ──
    eq_parts = []
    if brightness_val != 0.0:
        eq_parts.append(f"brightness={brightness_val:.4f}")
    if contrast_val != 1.0:
        eq_parts.append(f"contrast={contrast_val:.4f}")
    if saturation_val != 1.0:
        eq_parts.append(f"saturation={saturation_val:.4f}")
    if eq_parts:
        vfilters.insert(0, "eq=" + ":".join(eq_parts))

    # Light sharpening — IMPROVES quality perception instead of degrading it
    sharpen_val = rng.uniform(0.3, 0.8)
    vfilters.append(f"unsharp=5:5:{sharpen_val:.2f}:5:5:0")

    # Ensure even dimensions for h264
    vfilters.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")

    if upscale:
        vfilters.append(f"scale=iw*{upscale_factor}:ih*{upscale_factor}:flags=lanczos")
        vfilters.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")

    # ── Assemble FFmpeg command ──
    args = list(input_args)

    if vfilters:
        args.extend(["-vf", ",".join(vfilters)])
    if afilters:
        args.extend(["-af", ",".join(afilters)])

    has_codec_set = "-c:v" in extra_args
    if not has_codec_set:
        # CRF 15-18 = HIGH QUALITY (lower CRF = better quality)
        # Each variant gets different CRF for unique encoding fingerprint
        crf = rng.randint(15, 18)
        args.extend(["-c:v", "libx264", "-preset", "slow", "-crf", str(crf)])

    # High quality audio
    args.extend(["-c:a", "aac", "-b:a", f"{rng.choice([192, 224, 256])}k"])

    if TransformType.METADATA_STRIP in transforms:
        # Strip original metadata but inject RANDOM fake metadata
        # (bitexact flag makes FB suspicious → shadowban/0 views)
        args.extend(["-map_metadata", "-1"])
        # Inject natural-looking random metadata
        fake_titles = [
            "VID_" + str(rng.randint(20240101, 20261231)),
            "video_" + str(rng.randint(1000, 9999)),
            "MOV_" + str(rng.randint(100, 999)),
            "clip_" + str(rng.randint(10000, 99999)),
        ]
        fake_encoders = [
            "Lavf60.16.100", "Lavf59.27.100", "Lavf58.76.100",
            "HandBrake 1.7.3", "iMovie 10.3",
        ]
        args.extend(["-metadata", f"title={rng.choice(fake_titles)}"])
        # Random creation date within last 30 days
        import time
        fake_ts = int(time.time()) - rng.randint(0, 30 * 86400)
        from datetime import datetime as _dt
        fake_date = _dt.fromtimestamp(fake_ts).strftime("%Y-%m-%dT%H:%M:%S")
        args.extend(["-metadata", f"creation_time={fake_date}"])
        args.extend(["-metadata", f"encoder={rng.choice(fake_encoders)}"])

    args.extend(extra_args)
    args.append(output_path)

    return args
