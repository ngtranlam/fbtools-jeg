import json
import shutil
from pathlib import Path
from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOWNLOADS_DIR = DATA_DIR / "downloads"
VARIANTS_DIR = DATA_DIR / "variants"
REPORTS_DIR = DATA_DIR / "reports"
TEMP_DIR = DATA_DIR / "temp"
CONFIG_FILE = DATA_DIR / "config.json"

# ── Video Studio ──────────────────────────────────────────
STUDIO_DIR = DATA_DIR / "studio"
STUDIO_SOURCES_DIR = STUDIO_DIR / "sources"   # clip gốc user upload
STUDIO_AUDIO_DIR = STUDIO_DIR / "audio"       # nhạc nền
STUDIO_BASE_DIR = STUDIO_DIR / "base"         # video đã ghép (bản gốc)
STUDIO_RENDERS_DIR = STUDIO_DIR / "renders"   # các biến thể render hàng loạt

for d in [
    DATA_DIR, DOWNLOADS_DIR, VARIANTS_DIR, REPORTS_DIR, TEMP_DIR,
    STUDIO_DIR, STUDIO_SOURCES_DIR, STUDIO_AUDIO_DIR, STUDIO_BASE_DIR, STUDIO_RENDERS_DIR,
]:
    d.mkdir(parents=True, exist_ok=True)


class AppConfig(BaseModel):
    #: Khoang nghi ngau nhien giua hai bai dang lien tiep (giay).
    #: Dang lien tiep khong nghi la dau hieu may chay tu dong ro nhat.
    publish_delay_min: int = 60
    publish_delay_max: int = 120
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    default_variants: int = 5
    max_variants: int = 10
    default_profile: str = "medium"
    video_format: str = "mp4"
    max_concurrent_jobs: int = 2
    upscale_enabled: bool = False
    upscale_factor: int = 2


def load_config() -> AppConfig:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        return AppConfig(**data)
    cfg = AppConfig()
    ffmpeg_bin = shutil.which("ffmpeg")
    ffprobe_bin = shutil.which("ffprobe")
    if ffmpeg_bin:
        cfg.ffmpeg_path = ffmpeg_bin
    if ffprobe_bin:
        cfg.ffprobe_path = ffprobe_bin
    save_config(cfg)
    return cfg


def save_config(cfg: AppConfig) -> None:
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg.model_dump(), f, indent=2)


config = load_config()
