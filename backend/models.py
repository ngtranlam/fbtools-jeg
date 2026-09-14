from __future__ import annotations

import enum
from datetime import datetime
from pydantic import BaseModel, Field


class Platform(str, enum.Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"

    UNKNOWN = "unknown"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── Download ──────────────────────────────────────────────

class DownloadRequest(BaseModel):
    url: str

class VideoInfo(BaseModel):
    id: str
    title: str
    description: str = ""
    filename: str
    filepath: str
    platform: Platform = Platform.UNKNOWN
    duration: float = 0
    width: int = 0
    height: int = 0
    filesize: int = 0
    thumbnail: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ── Spoof ─────────────────────────────────────────────────

class TransformType(str, enum.Enum):
    CROP = "crop"
    BRIGHTNESS = "brightness"
    CONTRAST = "contrast"
    SATURATION = "saturation"
    HUE_SHIFT = "hue_shift"
    SPEED = "speed"
    SCALE = "scale"
    BITRATE = "bitrate"
    FRAMERATE = "framerate"
    CODEC = "codec"
    MIRROR = "mirror"
    ROTATION = "rotation"
    NOISE = "noise"
    AUDIO_PITCH = "audio_pitch"
    TRIM = "trim"
    METADATA_STRIP = "metadata_strip"
    PIXEL_SHIFT = "pixel_shift"


class SpoofRequest(BaseModel):
    video_id: str
    num_variants: int = Field(default=5, ge=1, le=10)
    profile: str = "medium"
    transforms: list[TransformType] | None = None
    upscale: bool = False
    upscale_factor: int = 2


class VariantInfo(BaseModel):
    id: str
    filename: str
    filepath: str
    transforms_applied: list[str] = []
    filesize: int = 0
    duration: float = 0
    width: int = 0
    height: int = 0


class SpoofJob(BaseModel):
    job_id: str
    video_id: str
    video_title: str = ""
    video_description: str = ""
    status: JobStatus = JobStatus.PENDING
    num_variants: int = 5
    completed_variants: int = 0
    variants: list[VariantInfo] = []
    started_at: str = ""
    finished_at: str = ""
    error: str = ""


# ── Checker ───────────────────────────────────────────────

class CheckRequest(BaseModel):
    video_ids: list[str] = []
    video_paths: list[str] = []

class FrameHash(BaseModel):
    position: str
    hash_value: str

class VideoHashResult(BaseModel):
    video_id: str
    filename: str
    frame_hashes: list[FrameHash] = []

class UniquenessReport(BaseModel):
    report_id: str
    total_videos: int
    unique_count: int
    duplicate_pairs: list[dict] = []
    results: list[VideoHashResult] = []
    all_unique: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ── Metadata ──────────────────────────────────────────────

class VideoMetadata(BaseModel):
    title: str = ""
    description: str = ""
    tags: list[str] = []
    author: str = ""
    creation_date: str = ""
    encoder: str = ""

class MetadataUpdateRequest(BaseModel):
    video_id: str
    metadata: VideoMetadata
