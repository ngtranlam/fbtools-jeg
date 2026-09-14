from __future__ import annotations

from backend.models import TransformType

# ──────────────────────────────────────────────────────────────────────
# PHILOSOPHY: Break the digital fingerprint WITHOUT degrading visual quality.
#
# Platform detection works by comparing:
#   1. File-level metadata (filename, container, creation date)
#   2. Codec fingerprint (bitrate, CRF, encoder settings)
#   3. Perceptual hash of sampled frames (pHash / dHash)
#   4. Audio fingerprint
#
# We exploit the fact that even TINY pixel-level changes (~1-2%) completely
# break perceptual hashes, while remaining invisible to the human eye.
# We do NOT need aggressive crop, noise, or color shifts.
# ──────────────────────────────────────────────────────────────────────

PROFILES: dict[str, dict] = {
    "light": {
        "name": "Nhẹ",
        "description": "Thay đổi tối thiểu — metadata + mã hóa lại + chỉnh màu nhẹ",
        "transforms": [
            TransformType.METADATA_STRIP,
            TransformType.BITRATE,
            TransformType.BRIGHTNESS,
            TransformType.CONTRAST,
            TransformType.SATURATION,
            TransformType.PIXEL_SHIFT,
        ],
        "ranges": {
            "brightness": (-0.015, 0.015),
            "contrast": (0.99, 1.01),
            "saturation": (0.98, 1.02),
            "bitrate_factor": (0.90, 1.10),
            "pixel_shift_max": 2,
        },
    },
    "medium": {
        "name": "Vừa",
        "description": "Hiệu quả và cân bằng — cắt nhẹ, chỉnh màu, đồng bộ tốc độ",
        "transforms": [
            TransformType.METADATA_STRIP,
            TransformType.CROP,
            TransformType.BRIGHTNESS,
            TransformType.CONTRAST,
            TransformType.SATURATION,
            TransformType.HUE_SHIFT,
            TransformType.SPEED,
            TransformType.BITRATE,
            TransformType.FRAMERATE,
            TransformType.AUDIO_PITCH,
            TransformType.PIXEL_SHIFT,
        ],
        "ranges": {
            "crop_pct": (0.005, 0.015),         # 0.5-1.5% — barely noticeable
            "brightness": (-0.02, 0.02),
            "contrast": (0.98, 1.02),
            "saturation": (0.97, 1.03),
            "hue_degrees": (-2, 2),
            "speed_factor": (0.99, 1.01),        # ±1% — duration stays ~same
            "bitrate_factor": (0.85, 1.15),
            "audio_pitch_pct": (-1, 1),
            "pixel_shift_max": 3,
        },
    },
    "heavy": {
        "name": "Mạnh",
        "description": "Thay đổi tối đa — vẫn đẹp, giữ nguyên chất lượng",
        "transforms": [
            TransformType.METADATA_STRIP,
            TransformType.CROP,
            TransformType.BRIGHTNESS,
            TransformType.CONTRAST,
            TransformType.SATURATION,
            TransformType.HUE_SHIFT,
            TransformType.SPEED,
            TransformType.SCALE,
            TransformType.BITRATE,
            TransformType.FRAMERATE,
            TransformType.MIRROR,
            TransformType.NOISE,
            TransformType.AUDIO_PITCH,
            TransformType.PIXEL_SHIFT,
        ],
        "ranges": {
            "crop_pct": (0.008, 0.02),           # 0.8-2% max — invisible crop
            "brightness": (-0.03, 0.03),          # very subtle
            "contrast": (0.97, 1.03),
            "saturation": (0.95, 1.05),
            "hue_degrees": (-3, 3),               # barely noticeable
            "speed_factor": (0.99, 1.01),         # ±1% — keeps duration same
            "scale_pct": (-2, 2),                 # ±2% scale
            "bitrate_factor": (0.80, 1.20),
            "noise_strength": (1, 3),             # very light grain — looks natural
            "audio_pitch_pct": (-1.5, 1.5),
            "pixel_shift_max": 4,
        },
    },
}


DEFAULT_RANGES = {
    "crop_pct": (0.005, 0.015),
    "brightness": (-0.02, 0.02),
    "contrast": (0.98, 1.02),
    "saturation": (0.97, 1.03),
    "hue_degrees": (-2, 2),
    "speed_factor": (0.99, 1.01),
    "scale_pct": (-2, 2),
    "bitrate_factor": (0.85, 1.15),
    "noise_strength": (1, 2),
    "audio_pitch_pct": (-1, 1),
    "pixel_shift_max": 3,
}


def get_profile(name: str) -> dict:
    return PROFILES.get(name, PROFILES["medium"])


def list_profiles() -> list[dict]:
    return [
        {"id": k, "name": v["name"], "description": v["description"], "transforms": [t.value for t in v["transforms"]]}
        for k, v in PROFILES.items()
    ]
