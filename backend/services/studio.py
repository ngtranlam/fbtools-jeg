"""Video Studio — cắt cảnh, ghép clip, chuyển cảnh, text, nhạc nền và render hàng loạt.

Luồng nghiệp vụ:
    1. Upload clip A / clip B (và nhạc nền) -> studio_assets
    2. Chọn đoạn cần lấy trên từng clip -> timeline (segments)
    3. Ghép lại + hiệu ứng chuyển cảnh + text on screen + nhạc -> video "base"
    4. Từ video base render ra N biến thể (mỗi bản nhạc khác, màu khác, spoof khác)
    5. Mỗi biến thể được ghi vào bảng `variants` để Content Studio đăng lên Fanpage
"""

from __future__ import annotations

import json
import logging
import random
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from backend.config import (
    STUDIO_AUDIO_DIR,
    STUDIO_BASE_DIR,
    STUDIO_RENDERS_DIR,
    STUDIO_SOURCES_DIR,
    TEMP_DIR,
)
from backend.database import get_db
from backend.utils.ffmpeg import available_filters, get_video_info, run_ffmpeg
from backend.utils.websocket import ws_manager

log = logging.getLogger(__name__)


# ══ Hằng số ════════════════════════════════════════════════

#: Hiệu ứng chuyển cảnh (map sang filter `xfade` của FFmpeg)
TRANSITIONS: list[dict] = [
    {"id": "none", "name": "Cắt thẳng", "desc": "Không hiệu ứng, chuyển ngay"},
    {"id": "fade", "name": "Mờ dần", "desc": "Hoà tan hai cảnh — an toàn nhất"},
    {"id": "fadeblack", "name": "Mờ qua đen", "desc": "Tối dần rồi sáng lại"},
    {"id": "fadewhite", "name": "Mờ qua trắng", "desc": "Sáng loá rồi hiện cảnh sau"},
    {"id": "slideleft", "name": "Trượt trái", "desc": "Cảnh mới đẩy từ phải sang"},
    {"id": "slideright", "name": "Trượt phải", "desc": "Cảnh mới đẩy từ trái sang"},
    {"id": "slideup", "name": "Trượt lên", "desc": "Hợp video dọc / Reels"},
    {"id": "slidedown", "name": "Trượt xuống", "desc": "Cảnh mới đổ từ trên xuống"},
    {"id": "wipeleft", "name": "Gạt trái", "desc": "Quét ngang xoá cảnh cũ"},
    {"id": "wiperight", "name": "Gạt phải", "desc": "Quét ngang chiều ngược lại"},
    {"id": "smoothleft", "name": "Lướt mượt trái", "desc": "Trượt có làm mềm biên"},
    {"id": "smoothup", "name": "Lướt mượt lên", "desc": "Rất hợp Reels / TikTok"},
    {"id": "circlecrop", "name": "Mở vòng tròn", "desc": "Bung ra từ tâm"},
    {"id": "rectcrop", "name": "Mở khung chữ nhật", "desc": "Bung ra dạng khung"},
    {"id": "radial", "name": "Quét quạt", "desc": "Xoay quét quanh tâm"},
    {"id": "distance", "name": "Tan biến", "desc": "Hoà trộn theo màu"},
    {"id": "pixelize", "name": "Vỡ điểm ảnh", "desc": "Vỡ hạt rồi nét lại"},
    {"id": "hblur", "name": "Nhoè ngang", "desc": "Nhoè rồi rõ — cảm giác nhanh"},
    {"id": "dissolve", "name": "Hoà tan hạt", "desc": "Tan theo nhiễu ngẫu nhiên"},
    {"id": "zoomin", "name": "Phóng to", "desc": "Zoom vào cảnh kế tiếp"},
]

_TRANSITION_IDS = {t["id"] for t in TRANSITIONS}

#: Bộ màu áp cho từng biến thể — để mỗi bản đăng lên trông khác nhau rõ rệt
EFFECT_LOOKS: list[dict] = [
    {"id": "original", "name": "Gốc", "filters": []},
    {"id": "warm", "name": "Ấm", "filters": [
        "eq=saturation=1.08:contrast=1.03",
        "colorbalance=rs=0.06:gs=0.01:bs=-0.05",
    ]},
    {"id": "cool", "name": "Lạnh", "filters": [
        "eq=saturation=1.05:contrast=1.04",
        "colorbalance=rs=-0.05:gs=0.00:bs=0.07",
    ]},
    {"id": "vivid", "name": "Rực rỡ", "filters": [
        "eq=saturation=1.22:contrast=1.08:brightness=0.01",
        "unsharp=5:5:0.8:5:5:0",
    ]},
    {"id": "cinematic", "name": "Điện ảnh", "filters": [
        "curves=preset=medium_contrast",
        "eq=saturation=0.94:contrast=1.06",
        "colorbalance=rs=-0.04:bs=0.06:rm=0.03",
    ]},
    {"id": "vintage", "name": "Hoài cổ", "filters": [
        "curves=preset=vintage",
        "eq=saturation=0.9:contrast=0.97",
    ]},
    {"id": "clarity", "name": "Nét căng", "filters": [
        "unsharp=7:7:1.1:7:7:0",
        "eq=contrast=1.07:saturation=1.06",
    ]},
    {"id": "soft", "name": "Dịu", "filters": [
        "eq=saturation=0.95:contrast=0.96:brightness=0.015",
        "gblur=sigma=0.4",
    ]},
    {"id": "sunset", "name": "Hoàng hôn", "filters": [
        "colorbalance=rs=0.10:gs=0.02:bs=-0.08:rm=0.05",
        "eq=saturation=1.12:contrast=1.04",
    ]},
    {"id": "mint", "name": "Bạc hà", "filters": [
        "colorbalance=gs=0.08:bs=0.04:rs=-0.05",
        "eq=saturation=1.10",
    ]},
    {"id": "punch", "name": "Đậm nét", "filters": [
        "curves=preset=strong_contrast",
        "eq=saturation=1.15",
        "unsharp=5:5:0.6:5:5:0",
    ]},
    {"id": "film", "name": "Chất phim", "filters": [
        "curves=preset=lighter",
        "eq=saturation=0.98:contrast=1.05",
        "noise=alls=4:allf=t",
    ]},
]

_LOOKS_BY_ID = {lk["id"]: lk for lk in EFFECT_LOOKS}

#: Mức tinh chỉnh tiếng gốc — đổi vân tay âm thanh mà vẫn nghe được bình thường.
#: pitch tính theo %, bass/treble theo dB.
AUDIO_TUNE_PRESETS: list[dict] = [
    {"id": "none", "name": "Giữ nguyên", "desc": "Không đổi gì — dễ bị nhận ra nhất",
     "pitch": 0.0, "bass": 0.0, "treble": 0.0},
    {"id": "light", "name": "Nhẹ", "desc": "Gần như không nghe ra khác biệt",
     "pitch": 1.5, "bass": 1.0, "treble": -0.5},
    {"id": "medium", "name": "Vừa", "desc": "Khuyên dùng — an toàn cho video có lời thoại",
     "pitch": 3.0, "bass": 2.0, "treble": -1.5},
    {"id": "strong", "name": "Mạnh", "desc": "Giọng hơi khác, chỉ nên dùng cho video không có lời",
     "pitch": -4.5, "bass": 3.0, "treble": 2.0},
]

_TUNE_BY_ID = {p["id"]: p for p in AUDIO_TUNE_PRESETS}

#: Khung hình chuẩn cho từng nền tảng
CANVAS_PRESETS: list[dict] = [
    {"id": "reels", "name": "Reels / TikTok (9:16)", "width": 1080, "height": 1920},
    {"id": "square", "name": "Vuông (1:1)", "width": 1080, "height": 1080},
    {"id": "feed", "name": "Feed dọc (4:5)", "width": 1080, "height": 1350},
    {"id": "landscape", "name": "Ngang (16:9)", "width": 1920, "height": 1080},
]

#: Font dùng cho text on screen — ưu tiên font hiển thị đủ dấu tiếng Việt.
#: Liệt kê cho cả Windows, macOS và Linux nên cùng một bản cài chạy được mọi máy.
_FONT_CANDIDATES = {
    "bold": [
        # Windows
        "C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf",
        # macOS
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ],
    "regular": [
        "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ],
    "black": [
        "C:/Windows/Fonts/seguibl.ttf", "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
}

#: Nơi quét font khi không tìm thấy ứng viên nào ở trên
_FONT_DIRS = [
    "C:/Windows/Fonts",
    "/System/Library/Fonts/Supplemental",
    "/System/Library/Fonts",
    "/Library/Fonts",
    str(Path.home() / "Library" / "Fonts"),
    "/usr/share/fonts",
]

_VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
_AUDIO_EXTS = {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".flac"}


def resolve_font(style: str = "bold") -> str:
    """Trả về đường dẫn font khả dụng đầu tiên cho kiểu chữ yêu cầu."""
    for candidate in _FONT_CANDIDATES.get(style, _FONT_CANDIDATES["bold"]):
        if Path(candidate).exists():
            return candidate

    # Dự phòng: quét thư mục font của hệ điều hành, lấy font đầu tiên tìm được
    for dir_path in _FONT_DIRS:
        d = Path(dir_path)
        if not d.exists():
            continue
        for pattern in ("*.ttf", "*.otf", "*.ttc"):
            for f in sorted(d.rglob(pattern)):
                return str(f)
    return ""


def _esc(path: str) -> str:
    """Escape đường dẫn Windows để nhét vào filtergraph của FFmpeg."""
    return str(path).replace("\\", "/").replace(":", "\\:")


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


#: Filter nào dùng cho việc gì — để báo lỗi bằng tiếng người, không phải tên kỹ thuật
_FILTER_PURPOSE = {
    "drawtext": "viết chữ lên video",
    "reverse": "phát ngược cảnh",
    "areverse": "phát ngược tiếng của cảnh",
    "gblur": "kiểu lấp khung nền mờ hai bên",
    "overlay": "kiểu lấp khung nền mờ hai bên",
    "xfade": "hiệu ứng chuyển cảnh",
    "acrossfade": "hoà tiếng khi chuyển cảnh",
    "atempo": "tinh chỉnh tiếng gốc",
    "asetrate": "tinh chỉnh tiếng gốc",
    "bass": "tinh chỉnh tiếng gốc",
    "treble": "tinh chỉnh tiếng gốc",
    "amix": "trộn nhạc nền với tiếng gốc",
    "afade": "nhạc nền vào/ra êm",
    "unsharp": "bộ màu của biến thể",
    "colorbalance": "bộ màu của biến thể",
    "eq": "bộ màu của biến thể",
    "noise": "nhiễu nhẹ khi tạo biến thể",
}

_FFMPEG_FIX_HINT = (
    "Bản FFmpeg trên máy này là bản rút gọn nên thiếu. Cách sửa: tải bản đầy đủ "
    "ở https://www.gyan.dev/ffmpeg/builds/ (file ffmpeg-release-full.7z), giải nén, "
    "thay thư mục FFmpeg cũ rồi mở lại tool. Máy Mac chạy: brew reinstall ffmpeg."
)


def _missing_filter_message(missing: list[str]) -> str:
    """Câu báo lỗi khi bản FFmpeg đang cài thiếu filter mà tool cần."""
    parts = []
    for name in missing:
        purpose = _FILTER_PURPOSE.get(name)
        parts.append(f"{name} ({purpose})" if purpose else name)
    return (f"FFmpeg trên máy này thiếu bộ lọc: {', '.join(parts)}. "
            f"{_FFMPEG_FIX_HINT}")


def _split_filter_graph(graph: str) -> list[str]:
    """Tách filter_complex thành từng filter một.

    Không tách thô bằng dấu phẩy được: dấu phẩy còn nằm trong tham số, ví dụ
    `enable='between(t,1,2)'`. Nên phải bỏ qua phần trong nháy và trong ngoặc.
    """
    out: list[str] = []
    buf: list[str] = []
    depth = 0
    quoted = False
    i = 0
    while i < len(graph):
        c = graph[i]
        if c == "\\" and i + 1 < len(graph):
            buf.append(c)
            i += 1
            buf.append(graph[i])
        elif quoted:
            buf.append(c)
            if c == "'":
                quoted = False
        elif c == "'":
            quoted = True
            buf.append(c)
        elif c == "(":
            depth += 1
            buf.append(c)
        elif c == ")":
            depth = max(0, depth - 1)
            buf.append(c)
        elif c in ",;" and depth == 0:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(c)
        i += 1
    out.append("".join(buf))
    return out


_LABEL_HEAD = re.compile(r"^\s*(?:\[[^\]]*\]\s*)+")
_LABEL_TAIL = re.compile(r"(?:\s*\[[^\]]*\])+\s*$")
_FILTER_HEAD = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*")


def _graph_filter_names(graph: str) -> list[str]:
    """Tên của mọi filter xuất hiện trong một filter_complex."""
    names: list[str] = []
    for element in _split_filter_graph(graph):
        core = _LABEL_TAIL.sub("", _LABEL_HEAD.sub("", element)).strip()
        m = _FILTER_HEAD.match(core)
        if m:
            names.append(m.group(0))
    return names


def check_graph_filters(args: list[str]) -> str:
    """Kiểm tra trước khi chạy: bản FFmpeg đang cài có đủ filter không.

    FFmpeg chỉ nói "Filter not found" mà không cho biết thiếu cái gì, nên người
    dùng không thể tự sửa. Hỏi trước để báo đúng tên và cách khắc phục.
    Trả về chuỗi rỗng nếu không có vấn đề.
    """
    have = available_filters()
    if not have:
        return ""  # Không hỏi được FFmpeg thì cứ chạy, để nó tự báo lỗi

    missing = sorted({
        name
        for i, a in enumerate(args)
        if a == "-filter_complex" and i + 1 < len(args)
        for name in _graph_filter_names(args[i + 1])
        if name not in have
    })
    return _missing_filter_message(missing) if missing else ""


def _ffmpeg_error(stderr: str) -> str:
    """Rút gọn stderr của FFmpeg thành thông báo người dùng đọc được.

    FFmpeg in cả trăm dòng metadata của từng input trước khi báo lỗi thật,
    nên phải lọc riêng các dòng lỗi thay vì cắt phần đuôi.
    """
    if not stderr:
        return "FFmpeg không trả về thông tin lỗi."

    # "Filter not found" là câu vô dụng nhất của FFmpeg: nó không nói thiếu cái
    # gì. Tên filter nằm ở một dòng khác ("No such filter: 'x'") mà bộ lọc theo
    # từ khoá bên dưới không bắt được. Xử riêng để câu báo lỗi có ích.
    missing = re.findall(r"No such filter:\s*'([^']+)'", stderr)
    if missing:
        return _missing_filter_message(sorted(set(missing)))

    keywords = ("error", "invalid", "failed", "no such file", "unable to",
                "not found", "cannot", "unsupported")
    hits = [
        line.strip() for line in stderr.splitlines()
        if any(k in line.lower() for k in keywords)
    ]
    if hits:
        return " | ".join(dict.fromkeys(hits[-3:]))
    return stderr.strip().splitlines()[-1][:300]


# ══ Quản lý asset ══════════════════════════════════════════

async def save_asset(
    temp_path: Path,
    original_name: str,
    kind: str = "video",
    source: str = "upload",
) -> dict:
    """Đưa file vừa upload vào kho asset của Studio và probe metadata."""
    ext = temp_path.suffix.lower() or (".mp4" if kind == "video" else ".mp3")
    dest_dir = STUDIO_SOURCES_DIR if kind == "video" else STUDIO_AUDIO_DIR
    asset_uid = uuid.uuid4().hex[:10]
    safe_stem = _sanitize(Path(original_name).stem)
    dest = dest_dir / f"{asset_uid}_{safe_stem}{ext}"

    shutil.move(str(temp_path), str(dest))

    try:
        probe = await get_video_info(dest)
    except (FileNotFoundError, OSError) as e:
        log.warning("Probe asset failed for %s: %s", dest, e)
        probe = {}

    has_audio = await _has_audio_stream(dest) if kind == "video" else True

    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO studio_assets
               (kind, name, filename, filepath, duration, width, height, fps,
                filesize, has_audio, source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            kind,
            Path(original_name).stem,
            dest.name,
            str(dest),
            probe.get("duration", 0),
            probe.get("width", 0),
            probe.get("height", 0),
            probe.get("fps", 30),
            dest.stat().st_size,
            1 if has_audio else 0,
            source,
        ),
    )
    await db.commit()

    return await get_asset(cursor.lastrowid)


async def import_from_library(filepath: str, name: str = "") -> dict:
    """Copy một video đã có (thư viện tải về / biến thể) vào kho Studio."""
    src = Path(filepath)
    if not src.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {filepath}")

    kind = "audio" if src.suffix.lower() in _AUDIO_EXTS else "video"
    dest_dir = STUDIO_SOURCES_DIR if kind == "video" else STUDIO_AUDIO_DIR
    asset_uid = uuid.uuid4().hex[:10]
    dest = dest_dir / f"{asset_uid}_{_sanitize(src.stem)}{src.suffix}"
    shutil.copy2(str(src), str(dest))

    return await save_asset_record(dest, name or src.stem, kind, source="library")


async def save_asset_record(path: Path, name: str, kind: str, source: str) -> dict:
    """Ghi một file đã nằm sẵn trong kho Studio vào DB."""
    try:
        probe = await get_video_info(path)
    except (FileNotFoundError, OSError):
        probe = {}
    has_audio = await _has_audio_stream(path) if kind == "video" else True

    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO studio_assets
               (kind, name, filename, filepath, duration, width, height, fps,
                filesize, has_audio, source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (kind, name, path.name, str(path), probe.get("duration", 0),
         probe.get("width", 0), probe.get("height", 0), probe.get("fps", 30),
         path.stat().st_size, 1 if has_audio else 0, source),
    )
    await db.commit()
    return await get_asset(cursor.lastrowid)


async def list_assets(kind: str | None = None) -> list[dict]:
    db = await get_db()
    if kind:
        cursor = await db.execute(
            "SELECT * FROM studio_assets WHERE kind = ? ORDER BY created_at DESC", (kind,)
        )
    else:
        cursor = await db.execute("SELECT * FROM studio_assets ORDER BY created_at DESC")
    return [_asset_dict(r) for r in await cursor.fetchall()]


async def get_asset(asset_id: int) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM studio_assets WHERE id = ?", (asset_id,))
    row = await cursor.fetchone()
    return _asset_dict(row) if row else None


async def delete_asset(asset_id: int) -> bool:
    asset = await get_asset(asset_id)
    if not asset:
        return False
    fp = Path(asset["filepath"])
    if fp.exists():
        try:
            fp.unlink()
        except OSError as e:
            log.warning("Không xoá được file asset %s: %s", fp, e)
    db = await get_db()
    await db.execute("DELETE FROM studio_assets WHERE id = ?", (asset_id,))
    await db.commit()
    return True


def _asset_dict(row) -> dict:
    d = dict(row)
    sub = "sources" if d["kind"] == "video" else "audio"
    d["media_url"] = f"/media/studio/{sub}/{d['filename']}"
    return d


def _sanitize(name: str, max_len: int = 60) -> str:
    import re
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name).strip(". ")
    return (safe[:max_len].rstrip(". ") or "clip")


async def _has_audio_stream(path: Path) -> bool:
    """Kiểm tra file có audio track không — quyết định cách dựng chuỗi âm thanh."""
    from backend.config import config
    import asyncio
    import subprocess

    cmd = [
        config.ffprobe_path, "-v", "quiet", "-select_streams", "a",
        "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path),
    ]
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, lambda: subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30,
        ))
    except (subprocess.TimeoutExpired, OSError) as e:
        log.warning("Probe audio stream failed for %s: %s", path, e)
        return False
    out = result.stdout.decode(errors="replace") if isinstance(result.stdout, bytes) else result.stdout
    return "audio" in (out or "")


# ══ Dựng câu lệnh ghép video ═══════════════════════════════

def resolve_tune(tune: dict | None) -> dict:
    """Chuẩn hoá cấu hình tinh chỉnh tiếng gốc về dạng số cụ thể."""
    tune = tune or {}
    preset_id = tune.get("preset", "none")

    if preset_id == "custom":
        values = {
            "pitch": float(tune.get("pitch", 0) or 0),
            "bass": float(tune.get("bass", 0) or 0),
            "treble": float(tune.get("treble", 0) or 0),
        }
    else:
        preset = _TUNE_BY_ID.get(preset_id, _TUNE_BY_ID["none"])
        values = {"pitch": preset["pitch"], "bass": preset["bass"], "treble": preset["treble"]}

    return {
        "preset": preset_id,
        "pitch": _clamp(values["pitch"], -8.0, 8.0),
        "bass": _clamp(values["bass"], -8.0, 8.0),
        "treble": _clamp(values["treble"], -8.0, 8.0),
    }


def build_audio_tune_filters(tune: dict | None, extra_tempo: float = 1.0) -> list[str]:
    """Chuỗi filter tinh chỉnh tiếng gốc.

    `asetrate` đổi cao độ nhưng kéo theo cả tốc độ, nên phải dùng `atempo` bù lại
    để tiếng vẫn khớp hình. `extra_tempo` dành cho biến thể có lệch tốc độ video.
    """
    t = resolve_tune(tune)
    filters: list[str] = []

    pitch_factor = 1.0 + t["pitch"] / 100.0
    if abs(t["pitch"]) > 0.01:
        filters.append(f"asetrate=44100*{pitch_factor:.6f}")
        filters.append("aresample=44100")

    # Bù tốc độ do đổi cao độ, cộng thêm lệch tốc độ của biến thể (nếu có)
    tempo = extra_tempo / pitch_factor
    if abs(tempo - 1.0) > 0.0005:
        filters.append(f"atempo={_clamp(tempo, 0.5, 2.0):.6f}")

    if abs(t["bass"]) > 0.01:
        filters.append(f"bass=g={t['bass']:.2f}:f=110:w=0.6")
    if abs(t["treble"]) > 0.01:
        filters.append(f"treble=g={t['treble']:.2f}:f=8000:w=0.6")

    return filters


def _fit_filter(fit: str, width: int, height: int) -> str:
    """Chuỗi filter đưa clip về đúng khung hình đích."""
    if fit == "contain":
        return (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black")
    if fit == "blur":
        # Nền mờ phía sau + clip gốc giữ nguyên tỉ lệ ở giữa
        return (f"split=2[bg][fg];"
                f"[bg]scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},gblur=sigma=28[bgb];"
                f"[fg]scale={width}:{height}:force_original_aspect_ratio=decrease[fgs];"
                f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2")
    # cover (mặc định) — lấp đầy khung, cắt phần thừa
    return (f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height}")


def _fit_text(text: str, font_path: str, size: int, max_width: float) -> tuple[str, int]:
    """Xuống dòng (và co chữ nếu cần) để text luôn nằm gọn trong khung hình.

    `drawtext` của FFmpeg không tự wrap — chữ dài sẽ bị tràn ra ngoài mép video.
    Đo bằng Pillow để biết chính xác chiều rộng thật của từng dòng.
    """
    try:
        from PIL import ImageFont
        pil_font = ImageFont.truetype(font_path, size) if font_path else None
    except Exception as e:  # font hỏng / thiếu Pillow
        log.debug("Không đo được chữ bằng Pillow: %s", e)
        pil_font = None

    def measure(s: str, at_size: int) -> float:
        if pil_font is None:
            return len(s) * at_size * 0.55  # ước lượng khi không đo được
        try:
            from PIL import ImageFont
            return ImageFont.truetype(font_path, at_size).getlength(s)
        except Exception:
            return len(s) * at_size * 0.55

    paragraphs = [p for p in text.replace("\r", "").split("\n")]
    words = [w for p in paragraphs for w in p.split() if w]

    # Co chữ tới khi từ dài nhất vừa một dòng (tránh trường hợp không thể wrap)
    effective = size
    while effective > 14 and words:
        if max(measure(w, effective) for w in words) <= max_width:
            break
        effective -= 2

    lines: list[str] = []
    for paragraph in paragraphs:
        if not paragraph.strip():
            lines.append("")
            continue
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}".strip()
            if current and measure(candidate, effective) > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)

    return "\n".join(lines), effective


def _drawtext_filters(texts: list[dict], width: int, height: int,
                      temp_files: list[Path]) -> list[str]:
    """Sinh các filter `drawtext` cho phần chữ hiển thị trên video."""
    filters: list[str] = []

    for i, item in enumerate(texts):
        content = (item.get("text") or "").strip()
        if not content:
            continue

        font_path = resolve_font(item.get("font_style", "bold"))
        size = int(_clamp(float(item.get("size", 64) or 64), 12, 300))

        # Chừa lề hai bên rồi wrap cho vừa khung
        wrapped, size = _fit_text(content, font_path, size, width * 0.88)
        lines = wrapped.split("\n")

        color = item.get("color", "#FFFFFF").lstrip("#") or "FFFFFF"
        opacity = _clamp(float(item.get("opacity", 1.0) or 1.0), 0.1, 1.0)

        line_height = int(size * 1.32)
        block_height = line_height * len(lines)

        # Vị trí khối chữ (toạ độ dòng đầu tiên, tính bằng pixel)
        position = item.get("position", "bottom")
        if position == "top":
            block_top = height * 0.10
            x_expr = "(w-text_w)/2"
        elif position == "center":
            block_top = (height - block_height) / 2
            x_expr = "(w-text_w)/2"
        elif position == "custom":
            x_pct = _clamp(float(item.get("x_pct", 50) or 50), 0, 100) / 100
            y_pct = _clamp(float(item.get("y_pct", 80) or 80), 0, 100) / 100
            block_top = (height - block_height) * y_pct
            x_expr = f"(w-text_w)*{x_pct:.4f}"
        else:  # bottom — canh mép dưới khối chữ, tránh tràn khi nhiều dòng
            block_top = height * 0.90 - block_height
            x_expr = "(w-text_w)/2"
        block_top = max(0.0, block_top)

        # Giới hạn thời gian hiển thị
        start = float(item.get("start", 0) or 0)
        end = item.get("end")
        if end is not None and float(end) > start:
            enable = f"enable='between(t,{start:.3f},{float(end):.3f})'"
        elif start > 0:
            enable = f"enable='gte(t,{start:.3f})'"
        else:
            enable = ""

        style = item.get("style", "shadow")

        # Mỗi dòng là một drawtext riêng. FFmpeg 8 tạo hình chữ bằng harfbuzz và
        # sẽ vẽ chính ký tự xuống dòng thành ô vuông rỗng nếu nhét nhiều dòng
        # vào một filter — nên tách dòng ở đây là cách duy nhất cho ra chữ sạch.
        for line_idx, line in enumerate(lines):
            if not line.strip():
                continue

            tf = TEMP_DIR / f"studio_text_{uuid.uuid4().hex[:8]}_{i}_{line_idx}.txt"
            tf.write_text(line, encoding="utf-8", newline="\n")
            temp_files.append(tf)

            parts = [
                f"textfile='{_esc(tf)}'",
                f"fontcolor={color}@{opacity:.2f}",
                f"fontsize={size}",
                f"x={x_expr}",
                f"y={block_top + line_idx * line_height:.1f}",
                "fix_bounds=1",
            ]
            if font_path:
                parts.insert(0, f"fontfile='{_esc(font_path)}'")

            if style == "box":
                box_color = item.get("box_color", "000000").lstrip("#") or "000000"
                box_opacity = _clamp(float(item.get("box_opacity", 0.55) or 0.55), 0, 1)
                parts += ["box=1", f"boxcolor={box_color}@{box_opacity:.2f}",
                          f"boxborderw={max(8, size // 5)}"]
            elif style == "outline":
                parts += [f"borderw={max(2, size // 18)}", "bordercolor=black@0.9"]
            else:  # shadow
                offset = max(2, size // 22)
                parts += ["shadowcolor=black@0.7", f"shadowx={offset}", f"shadowy={offset}"]

            if enable:
                parts.append(enable)

            filters.append("drawtext=" + ":".join(parts))

    return filters


def build_compose_command(
    timeline: dict,
    assets: dict[int, dict],
    output_path: Path,
    temp_files: list[Path],
) -> tuple[list[str], float]:
    """Dựng lệnh FFmpeg ghép toàn bộ timeline thành 1 video.

    Trả về (args, tổng thời lượng dự kiến).
    """
    canvas = timeline.get("canvas") or {}
    width = int(canvas.get("width", 1080))
    height = int(canvas.get("height", 1920))
    fps = int(canvas.get("fps", 30))
    fit = canvas.get("fit", "cover")

    segments = [s for s in (timeline.get("segments") or []) if s.get("asset_id")]
    if not segments:
        raise ValueError("Timeline chưa có cảnh nào. Hãy chọn ít nhất 1 đoạn video.")

    transitions = timeline.get("transitions") or []
    audio_cfg = timeline.get("audio") or {}
    texts = timeline.get("texts") or []

    inputs: list[str] = []
    filter_parts: list[str] = []
    seg_durations: list[float] = []
    video_labels: list[str] = []
    audio_labels: list[str] = []

    silent_input_indices: list[int] = []
    input_index = 0

    # ── Từng cảnh: cắt đoạn + đưa về khung chuẩn ──────────
    for i, seg in enumerate(segments):
        asset = assets.get(int(seg["asset_id"]))
        if not asset:
            raise ValueError(
                f"Cảnh #{i + 1} đang dùng một clip đã bị xoá khỏi kho. "
                f"Hãy xoá cảnh đó ở bước 2 (nút 'Xoá cảnh lỗi'), hoặc tải lại clip lên."
            )

        asset_duration = float(asset.get("duration") or 0)
        start = max(0.0, float(seg.get("start", 0) or 0))
        end = seg.get("end")
        if end is None or float(end) <= start:
            end = asset_duration if asset_duration > start else start + 1.0
        end = float(end)
        if asset_duration > 0:
            end = min(end, asset_duration)
        duration = max(0.1, end - start)
        seg_durations.append(duration)

        inputs += ["-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", asset["filepath"]]
        seg_input_idx = input_index
        input_index += 1

        # Đảo ngược: cảnh phát từ cuối về đầu. `reverse` phải nằm sau khi đã đưa
        # về khung chuẩn, và phải kèm `areverse` cho tiếng — nếu không thì hình
        # chạy ngược mà tiếng vẫn xuôi.
        rev = ",reverse" if seg.get("reverse") else ""
        arev = ",areverse" if seg.get("reverse") else ""

        vlabel = f"v{i}"
        filter_parts.append(
            f"[{seg_input_idx}:v]{_fit_filter(fit, width, height)},"
            f"fps={fps},setsar=1,format=yuv420p{rev},setpts=PTS-STARTPTS[{vlabel}]"
        )
        video_labels.append(vlabel)

        alabel = f"a{i}"
        if asset.get("has_audio"):
            filter_parts.append(
                f"[{seg_input_idx}:a]aformat=sample_fmts=fltp:sample_rates=44100:"
                f"channel_layouts=stereo{arev},asetpts=PTS-STARTPTS[{alabel}]"
            )
        else:
            # Clip câm -> chèn một luồng im lặng cùng độ dài để chuỗi audio không đứt
            silent_input_indices.append(input_index)
            inputs += ["-f", "lavfi", "-t", f"{duration:.3f}",
                       "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
            filter_parts.append(f"[{input_index}:a]asetpts=PTS-STARTPTS[{alabel}]")
            input_index += 1
        audio_labels.append(alabel)

    # ── Nối các cảnh bằng hiệu ứng chuyển cảnh ────────────
    cur_v = video_labels[0]
    cur_a = audio_labels[0]
    total_duration = seg_durations[0]

    for i in range(1, len(segments)):
        trans = transitions[i - 1] if i - 1 < len(transitions) else {}
        trans_type = trans.get("type", "fade")
        if trans_type not in _TRANSITION_IDS:
            trans_type = "fade"

        next_seg_duration = seg_durations[i]
        max_trans = max(0.0, min(total_duration, next_seg_duration) - 0.05)
        trans_duration = _clamp(float(trans.get("duration", 0.5) or 0.5), 0.05, 2.5)
        trans_duration = min(trans_duration, max_trans)

        out_v = f"vx{i}"
        out_a = f"ax{i}"

        if trans_type == "none" or trans_duration <= 0.05:
            filter_parts.append(f"[{cur_v}][{video_labels[i]}]concat=n=2:v=1:a=0[{out_v}]")
            filter_parts.append(f"[{cur_a}][{audio_labels[i]}]concat=n=2:v=0:a=1[{out_a}]")
            total_duration += next_seg_duration
        else:
            offset = max(0.0, total_duration - trans_duration)
            filter_parts.append(
                f"[{cur_v}][{video_labels[i]}]xfade=transition={trans_type}:"
                f"duration={trans_duration:.3f}:offset={offset:.3f}[{out_v}]"
            )
            filter_parts.append(
                f"[{cur_a}][{audio_labels[i]}]acrossfade=d={trans_duration:.3f}:"
                f"c1=tri:c2=tri[{out_a}]"
            )
            total_duration += next_seg_duration - trans_duration

        cur_v, cur_a = out_v, out_a

    # ── Text on screen ────────────────────────────────────
    text_filters = _drawtext_filters(texts, width, height, temp_files)
    if text_filters:
        filter_parts.append(f"[{cur_v}]" + ",".join(text_filters) + "[vtxt]")
        cur_v = "vtxt"

    # ── Âm thanh: nhạc nền / giữ tiếng gốc / trộn cả hai ──
    audio_mode = audio_cfg.get("mode", "original")
    music_asset = None
    if audio_mode in ("music", "mix") and audio_cfg.get("asset_id"):
        music_asset = assets.get(int(audio_cfg["asset_id"]))

    final_audio_label = cur_a

    if music_asset:
        music_volume = _clamp(float(audio_cfg.get("volume", 1.0) or 1.0), 0, 3)
        music_start = max(0.0, float(audio_cfg.get("music_start", 0) or 0))
        inputs += ["-stream_loop", "-1", "-ss", f"{music_start:.3f}",
                   "-i", music_asset["filepath"]]
        music_idx = input_index
        input_index += 1

        fade_out_start = max(0.0, total_duration - 1.0)
        filter_parts.append(
            f"[{music_idx}:a]aformat=sample_fmts=fltp:sample_rates=44100:"
            f"channel_layouts=stereo,atrim=0:{total_duration:.3f},asetpts=PTS-STARTPTS,"
            f"volume={music_volume:.3f},afade=t=in:st=0:d=0.4,"
            f"afade=t=out:st={fade_out_start:.3f}:d=1.0[music]"
        )

        if audio_mode == "mix":
            original_volume = _clamp(float(audio_cfg.get("original_volume", 0.25) or 0.25), 0, 3)
            tune_chain = build_audio_tune_filters(audio_cfg.get("tune"))
            chain = tune_chain + [f"volume={original_volume:.3f}"]
            filter_parts.append(f"[{cur_a}]{','.join(chain)}[origv]")
            filter_parts.append(
                "[origv][music]amix=inputs=2:duration=first:dropout_transition=0,"
                "aresample=44100[aout]"
            )
        else:
            # Nhạc thay thế hoàn toàn tiếng gốc. FFmpeg vẫn bắt buộc mọi nhánh
            # filter phải có đích, nên tiếng gốc được đổ vào anullsink.
            filter_parts.append(f"[{cur_a}]anullsink")
            filter_parts.append("[music]anull[aout]")
        final_audio_label = "aout"
    else:
        original_volume = _clamp(float(audio_cfg.get("original_volume", 1.0) or 1.0), 0, 3)
        if audio_mode == "mute":
            original_volume = 0.0
            chain = [f"volume={original_volume:.3f}", "aresample=44100"]
        else:
            chain = build_audio_tune_filters(audio_cfg.get("tune")) + [
                f"volume={original_volume:.3f}", "aresample=44100",
            ]
        filter_parts.append(f"[{cur_a}]{','.join(chain)}[aout]")
        final_audio_label = "aout"

    args = list(inputs)
    args += ["-filter_complex", ";".join(filter_parts)]
    args += ["-map", f"[{cur_v}]", "-map", f"[{final_audio_label}]"]
    args += [
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", str(fps),
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        "-movflags", "+faststart",
        "-t", f"{total_duration:.3f}",
    ]

    # Xoá sạch metadata của clip nguồn. FFmpeg mặc định chép metadata từ input
    # đầu tiên sang output, nên video tải từ TikTok sẽ mang theo cả ID video gốc
    # (comment "vid:...") và mã băm nội bộ — nền tảng đọc metadata là biết ngay
    # video lấy từ đâu. Phải cắt ngay ở bản ghép, không đợi tới bước nhân bản.
    args += _clean_metadata_args()
    args.append(str(output_path))

    return args, total_duration


def _clean_metadata_args(rng: random.Random | None = None) -> list[str]:
    """Xoá metadata gốc và thay bằng thông tin trông tự nhiên.

    Không dùng cờ `-bitexact`: nó để lại dấu vết "được xử lý bằng máy" rõ ràng.
    """
    r = rng or random.Random()
    fake_titles = [
        f"VID_{r.randint(20240101, 20261231)}",
        f"video_{r.randint(1000, 9999)}",
        f"MOV_{r.randint(100, 999)}",
        f"IMG_{r.randint(1000, 9999)}",
    ]
    fake_encoders = [
        "Lavf60.16.100", "Lavf59.27.100", "Lavf58.76.100",
        "HandBrake 1.7.3", "iMovie 10.3",
    ]
    fake_ts = datetime.now().timestamp() - r.randint(0, 21 * 86400)
    fake_date = datetime.fromtimestamp(fake_ts).strftime("%Y-%m-%dT%H:%M:%S")

    return [
        "-map_metadata", "-1",
        "-map_chapters", "-1",
        "-metadata", f"title={r.choice(fake_titles)}",
        "-metadata", f"encoder={r.choice(fake_encoders)}",
        "-metadata", f"creation_time={fake_date}",
    ]


# ══ Dự án ══════════════════════════════════════════════════

async def create_project(name: str, timeline: dict) -> dict:
    db = await get_db()
    cursor = await db.execute(
        "INSERT INTO studio_projects (name, timeline) VALUES (?, ?)",
        (name or "Dự án mới", json.dumps(timeline, ensure_ascii=False)),
    )
    await db.commit()
    return await get_project(cursor.lastrowid)


async def update_project(project_id: int, name: str | None, timeline: dict | None) -> dict | None:
    db = await get_db()
    if name is not None:
        await db.execute(
            "UPDATE studio_projects SET name = ?, updated_at = datetime('now') WHERE id = ?",
            (name, project_id),
        )
    if timeline is not None:
        await db.execute(
            "UPDATE studio_projects SET timeline = ?, updated_at = datetime('now') WHERE id = ?",
            (json.dumps(timeline, ensure_ascii=False), project_id),
        )
    await db.commit()
    return await get_project(project_id)


async def get_project(project_id: int) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM studio_projects WHERE id = ?", (project_id,))
    row = await cursor.fetchone()
    if not row:
        return None
    d = dict(row)
    raw_timeline = d.get("timeline") or "{}"
    try:
        d["timeline"] = json.loads(raw_timeline)
    except json.JSONDecodeError:
        d["timeline"] = {}
    if d.get("base_filename"):
        d["base_url"] = f"/media/studio/base/{d['base_filename']}"

    # Bản ghép có còn khớp với thiết lập hiện tại không
    d["base_stale"] = _is_base_stale(d)
    return d


#: Các khoá của timeline không ảnh hưởng tới bản ghép, nên đổi chúng không có
#: nghĩa là phải ghép lại. `hook` chỉ dùng lúc nhân bản, mỗi biến thể tự ghép
#: riêng — nếu tính vào đây thì cứ chạm vào ô hook là hiện cảnh báo "bản ghép cũ"
#: một cách vô lý.
_BASE_IRRELEVANT_KEYS = ("hook",)


def _base_signature(timeline: dict | None) -> str:
    """Dấu vân tay của những phần timeline thực sự quyết định bản ghép."""
    tl = {k: v for k, v in (timeline or {}).items() if k not in _BASE_IRRELEVANT_KEYS}
    return json.dumps(tl, ensure_ascii=False, sort_keys=True)


def _is_base_stale(project: dict) -> bool:
    """True khi timeline đã đổi so với lúc ghép -> cần ghép lại."""
    if not project.get("base_filename"):
        return False
    saved = project.get("base_timeline") or ""
    if not saved:
        # Dự án ghép từ bản cũ chưa lưu mốc này — không kết luận là cũ
        return False

    current = _base_signature(project.get("timeline"))
    if current == saved:
        return False

    # Mốc cũ có thể đã lưu kèm `hook`; so lại sau khi bỏ khoá đó ra để bản ghép
    # từ trước bản cập nhật này không bị báo cũ oan.
    try:
        return current != _base_signature(json.loads(saved))
    except (json.JSONDecodeError, TypeError):
        return True


async def list_projects(limit: int = 50) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        """SELECT p.*, (SELECT COUNT(*) FROM studio_renders r WHERE r.project_id = p.id) AS render_count
           FROM studio_projects p ORDER BY p.updated_at DESC LIMIT ?""",
        (limit,),
    )
    out = []
    for row in await cursor.fetchall():
        d = dict(row)
        try:
            d["timeline"] = json.loads(d.get("timeline") or "{}")
        except json.JSONDecodeError:
            d["timeline"] = {}
        if d.get("base_filename"):
            d["base_url"] = f"/media/studio/base/{d['base_filename']}"
        out.append(d)
    return out


async def delete_project(project_id: int) -> bool:
    project = await get_project(project_id)
    if not project:
        return False
    if project.get("base_filepath"):
        _try_delete(Path(project["base_filepath"]))
    db = await get_db()
    await db.execute("DELETE FROM studio_projects WHERE id = ?", (project_id,))
    await db.commit()
    return True


def _try_delete(path: Path) -> bool:
    """Xoá file, bỏ qua nếu đang bị khoá. Trả True khi xoá được."""
    try:
        path.unlink(missing_ok=True)
        return True
    except OSError as e:
        # Windows khoá file đang mở (trình duyệt phát video, FFmpeg chưa nhả...)
        log.info("Chưa xoá được %s (%s) — để dọn lần sau", path.name, e)
        return False


def _cleanup_orphan_bases(project_id: int, keep: Path) -> None:
    """Dọn các bản ghép cũ của dự án còn sót lại vì lần trước bị khoá."""
    try:
        for f in STUDIO_BASE_DIR.glob(f"base_{project_id}_*.mp4"):
            if f != keep:
                _try_delete(f)
    except OSError as e:
        log.debug("Bỏ qua dọn bản ghép cũ: %s", e)


async def compose_project(project_id: int, timeline: dict | None = None) -> dict:
    """Ghép timeline thành video base — bước xem trước trước khi render hàng loạt."""
    project = await get_project(project_id)
    if not project:
        return {"error": "Không tìm thấy dự án"}

    tl = timeline if timeline is not None else project["timeline"]
    assets = {a["id"]: a for a in await list_assets()}

    out_name = f"base_{project_id}_{uuid.uuid4().hex[:8]}.mp4"
    out_path = STUDIO_BASE_DIR / out_name
    temp_files: list[Path] = []

    try:
        args, expected_duration = build_compose_command(tl, assets, out_path, temp_files)
    except ValueError as e:
        return {"error": str(e)}

    await ws_manager.broadcast({
        "type": "studio_compose",
        "project_id": project_id,
        "status": "processing",
        "message": "Đang ghép video...",
    })

    problem = check_graph_filters(args)
    if problem:
        log.error("Compose project %s: %s", project_id, problem)
        return {"error": f"Ghép video thất bại — {problem}"}

    log.info("Compose project %s -> %s (%.2fs)", project_id, out_name, expected_duration)
    result = await run_ffmpeg(args)

    for tf in temp_files:
        _try_delete(tf)

    if result.returncode != 0 or not out_path.exists():
        reason = _ffmpeg_error(result.stderr or "")
        log.error("Compose project %s failed: %s", project_id, (result.stderr or "")[-2000:])
        await ws_manager.broadcast({
            "type": "studio_compose",
            "project_id": project_id,
            "status": "failed",
            "message": "Ghép video thất bại",
        })
        return {"error": f"Ghép video thất bại — {reason}"}

    # Xoá bản base cũ để không rác ổ đĩa.
    # Trên Windows, file đang được trình duyệt phát (thẻ video ở bước 5) sẽ bị khoá
    # và ném PermissionError — `missing_ok` không chắn được lỗi đó. Nếu để lọt,
    # cả bước ghép sẽ báo thất bại dù video mới đã dựng xong.
    old_base = project.get("base_filepath")
    if old_base and old_base != str(out_path):
        _try_delete(Path(old_base))

    _cleanup_orphan_bases(project_id, keep=out_path)

    try:
        probe = await get_video_info(out_path)
    except (FileNotFoundError, OSError):
        probe = {}

    # Lưu luôn timeline dùng để ghép. Nhờ vậy về sau biết được người dùng có sửa
    # gì (đổi nhạc, thêm cảnh...) mà quên ghép lại hay không — nếu quên, các biến
    # thể sẽ mang tiếng và hình của bản ghép cũ.
    timeline_json = _base_signature(tl)

    db = await get_db()
    await db.execute(
        """UPDATE studio_projects SET timeline = ?, base_timeline = ?, base_filename = ?,
               base_filepath = ?, base_duration = ?, status = 'composed',
               updated_at = datetime('now')
           WHERE id = ?""",
        (json.dumps(tl, ensure_ascii=False), timeline_json, out_name, str(out_path),
         probe.get("duration", expected_duration), project_id),
    )
    await db.commit()

    await ws_manager.broadcast({
        "type": "studio_compose",
        "project_id": project_id,
        "status": "completed",
        "message": "Ghép xong!",
        "base_url": f"/media/studio/base/{out_name}",
    })

    return {
        "success": True,
        "base_url": f"/media/studio/base/{out_name}",
        "base_filename": out_name,
        "duration": probe.get("duration", expected_duration),
        "width": probe.get("width", 0),
        "height": probe.get("height", 0),
        "filesize": out_path.stat().st_size,
    }


# ══ Render hàng loạt ═══════════════════════════════════════

_batch_jobs: dict[str, dict] = {}


def get_batch_job(job_id: str) -> dict | None:
    return _batch_jobs.get(job_id)


def list_batch_jobs() -> list[dict]:
    return sorted(_batch_jobs.values(), key=lambda j: j.get("started_at", ""), reverse=True)


def _build_variant_filters(
    look_id: str,
    rng: random.Random,
    width: int,
    height: int,
) -> tuple[list[str], dict]:
    """Chuỗi filter cho một biến thể: bộ màu + zoom + spoof pixel."""
    look = _LOOKS_BY_ID.get(look_id, _LOOKS_BY_ID["original"])
    filters: list[str] = []
    recipe: dict = {"look": look["id"], "look_name": look["name"]}

    # Zoom nhẹ ngẫu nhiên — đổi khung hình từng bản, mắt thường khó nhận ra
    zoom = round(rng.uniform(1.0, 1.06), 4)
    if zoom > 1.001:
        filters.append(
            f"crop=iw/{zoom:.4f}:ih/{zoom:.4f}:(iw-iw/{zoom:.4f})/2:(ih-ih/{zoom:.4f})/2"
        )
        filters.append(f"scale={width}:{height}")
    recipe["zoom"] = zoom

    filters.extend(look["filters"])

    # Vi chỉnh màu để phá perceptual hash mà không đổi cảm quan
    brightness = round(rng.uniform(-0.02, 0.02), 4)
    contrast = round(rng.uniform(0.98, 1.02), 4)
    saturation = round(rng.uniform(0.98, 1.02), 4)
    filters.append(
        f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}"
    )
    recipe["micro_eq"] = {"brightness": brightness, "contrast": contrast,
                          "saturation": saturation}

    # Dịch pixel 1-3px rồi pad lại đúng kích thước
    shift_x = rng.randint(1, 3)
    shift_y = rng.randint(1, 3)
    filters.append(
        f"crop=iw-{shift_x}:ih-{shift_y}:{shift_x}:0,pad=iw+{shift_x}:ih+{shift_y}:0:{shift_y}"
    )
    recipe["pixel_shift"] = [shift_x, shift_y]

    # Xoay màu rất nhẹ — mắt thường không thấy nhưng đổi giá trị từng điểm ảnh
    hue = round(rng.uniform(-2.0, 2.0), 2)
    filters.append(f"hue=h={hue}")
    recipe["hue"] = hue

    sharpen = round(rng.uniform(0.2, 0.7), 2)
    filters.append(f"unsharp=5:5:{sharpen}:5:5:0")
    filters.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")

    return filters, recipe


def _build_variant_command(
    base_path: Path,
    output_path: Path,
    look_id: str,
    music: dict | None,
    rng: random.Random,
    width: int,
    height: int,
    fps: int,
    base_duration: float,
    music_volume: float,
    keep_original_audio: bool,
    audio_tune: dict | None = None,
) -> tuple[list[str], dict]:
    """Dựng lệnh FFmpeg cho một biến thể."""
    vfilters, recipe = _build_variant_filters(look_id, rng, width, height)

    # Tốc độ lệch ±1%: mắt thường không nhận ra (20 giây chỉ lệch 0.2 giây)
    # nhưng làm đổi toàn bộ mốc thời gian của khung hình và âm thanh, nên phá
    # được cách nhận diện dựa trên dấu vân tay theo thời gian.
    speed = round(rng.uniform(0.99, 1.01), 5)
    vfilters.append(f"setpts={1 / speed:.6f}*PTS")
    recipe["speed"] = speed
    new_duration = base_duration / speed

    args: list[str] = ["-i", str(base_path)]
    filter_parts = [f"[0:v]{','.join(vfilters)}[vout]"]

    fade_out_start = max(0.0, new_duration - 1.0)

    if music:
        args += ["-stream_loop", "-1", "-i", music["filepath"]]
        if keep_original_audio:
            filter_parts.append(
                f"[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
                f"atrim=0:{new_duration:.3f},asetpts=PTS-STARTPTS,volume={music_volume:.3f},"
                f"afade=t=out:st={fade_out_start:.3f}:d=1.0[mus]"
            )
            filter_parts.append(f"[0:a]atempo={speed:.5f},volume=0.25[orig]")
            filter_parts.append(
                "[orig][mus]amix=inputs=2:duration=first:dropout_transition=0,"
                "aresample=44100[aout]"
            )
        else:
            filter_parts.append(
                f"[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
                f"atrim=0:{new_duration:.3f},asetpts=PTS-STARTPTS,volume={music_volume:.3f},"
                f"afade=t=in:st=0:d=0.4,afade=t=out:st={fade_out_start:.3f}:d=1.0,"
                f"aresample=44100[aout]"
            )
        recipe["music"] = {"id": music["id"], "name": music["name"]}
    else:
        # Giữ tiếng gốc: mỗi bản lệch cao độ và âm sắc một chút quanh mức người
        # dùng đã chọn, để các bản không chỉ khác hình mà còn khác cả tiếng.
        base_tune = resolve_tune(audio_tune)
        variant_tune = {
            "preset": "custom",
            "pitch": round(base_tune["pitch"] + rng.uniform(-1.2, 1.2), 3),
            "bass": round(base_tune["bass"] + rng.uniform(-0.8, 0.8), 2),
            "treble": round(base_tune["treble"] + rng.uniform(-0.8, 0.8), 2),
        }
        chain = build_audio_tune_filters(variant_tune, extra_tempo=speed)
        chain.append("aresample=44100")
        filter_parts.append(f"[0:a]{','.join(chain)}[aout]")
        recipe["music"] = None
        recipe["audio_tune"] = variant_tune

    crf = rng.randint(18, 21)
    # Đổi khung hình/giây quanh giá trị gốc — thêm một điểm khác biệt khi mã hoá
    out_fps = rng.choice([fps, 29.97, 30, 25, 24]) if fps >= 25 else fps
    recipe["crf"] = crf
    recipe["fps"] = out_fps

    args += ["-filter_complex", ";".join(filter_parts)]
    args += ["-map", "[vout]", "-map", "[aout]"]
    args += [
        "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
        "-pix_fmt", "yuv420p", "-r", str(out_fps),
        "-c:a", "aac", "-b:a", f"{rng.choice([160, 192, 224])}k",
        "-movflags", "+faststart",
    ]
    args += _clean_metadata_args(rng)
    args += ["-shortest", str(output_path)]
    return args, recipe


# ══ Ghép ngẫu nhiên ═══════════════════════════════════════
#
# Một clip dài chứa rất nhiều đoạn dùng được. Thay vì đăng đi đăng lại đúng một
# bản ghép lên nhiều Fanpage — thứ nền tảng nhận ra ngay — mỗi biến thể lấy một
# đoạn khác nhau: cảnh mở đầu lấy trong clip A, phần thân lấy trong clip B.

HOOK_DEFAULTS = {"scenes": 1, "min_len": 5.0, "max_len": 10.0}


def _rng_for(seed: int, idx: int, salt: str) -> random.Random:
    """Bộ ngẫu nhiên cố định theo (mã trộn, số thứ tự bản, phần nào).

    Bản xem trước và bản render thật phải ra y hệt nhau — nếu mỗi lần gọi lại
    bốc một kiểu thì xem trước chẳng còn ý nghĩa gì. Cùng `seed` thì cùng kết quả,
    đổi `seed` là trộn lại toàn bộ.
    """
    return random.Random(f"{seed}:{idx}:{salt}")


def _pick_windows(duration: float, count: int, min_len: float, max_len: float,
                  rng: random.Random, idx: int, total: int) -> list[tuple[float, float]]:
    """Chọn `count` đoạn ngẫu nhiên trong một clip, cho biến thể thứ `idx`.

    Không bốc hoàn toàn ngẫu nhiên: clip được chia thành từng vùng, mỗi đoạn lấy
    trong vùng của nó nên các đoạn không bao giờ chồng lên nhau và vẫn đúng thứ
    tự thời gian. Vị trí trong vùng thì xoay theo số thứ tự biến thể, nên bản số 1
    và bản số 2 chắc chắn lấy chỗ khác nhau chứ không phụ thuộc may rủi.
    """
    count = max(1, int(count))
    total = max(1, int(total))
    zone = duration / count

    windows: list[tuple[float, float]] = []
    for s in range(count):
        length = _clamp(rng.uniform(min_len, max_len), 0.5, max(0.5, zone - 0.05))
        span = max(0.0, zone - length)
        frac = (((idx + s) % total) + rng.random()) / total
        start = s * zone + span * frac
        windows.append((round(start, 3), round(start + length, 3)))
    return windows


def _hook_cfg(hook: dict) -> dict:
    """Đọc cấu hình hook về đúng kiểu và trong khoảng cho phép."""
    scenes = int(_clamp(float(hook.get("scenes", 1) or 1), 1, 3))
    min_len = _clamp(float(hook.get("min_len", 5) or 5), 1.0, 60.0)
    max_len = _clamp(float(hook.get("max_len", 10) or 10), min_len, 60.0)
    return {"scenes": scenes, "min_len": min_len, "max_len": max_len,
            "seed": int(hook.get("seed") or 0)}


def _body_cfg(hook: dict) -> dict:
    b = hook.get("body") or {}
    min_len = _clamp(float(b.get("min_len", 10) or 10), 1.0, 300.0)
    max_len = _clamp(float(b.get("max_len", 15) or 15), min_len, 300.0)
    return {"enabled": bool(b.get("enabled")), "asset_id": b.get("asset_id"),
            "min_len": min_len, "max_len": max_len}


def _body_asset(hook: dict, segments: list[dict], replace: int,
                assets: dict[int, dict]) -> dict | None:
    """Clip dùng cho phần thân. Chưa chọn thì lấy chính clip của cảnh thân đầu."""
    b = _body_cfg(hook)
    if b["asset_id"]:
        return assets.get(int(b["asset_id"]))
    rest = segments[replace:]
    return assets.get(int(rest[0]["asset_id"])) if rest else None


def build_hook_timeline(timeline: dict, hook: dict, assets: dict[int, dict],
                        idx: int, total: int) -> dict:
    """Bản sao timeline đã thay cảnh đầu (và cả phần thân nếu bật) bằng đoạn ngẫu nhiên.

    Trả về chính `timeline` nếu không bật hoặc cấu hình không dùng được — khi đó
    biến thể chạy y như cũ.
    """
    if not hook or not hook.get("enabled"):
        return timeline

    asset = assets.get(int(hook.get("asset_id") or 0))
    if not asset or asset.get("kind") == "audio":
        return timeline

    cfg = _hook_cfg(hook)
    duration = float(asset.get("duration") or 0)
    if duration < cfg["scenes"] * cfg["min_len"]:
        return timeline

    segments = list(timeline.get("segments") or [])
    transitions = list(timeline.get("transitions") or [])
    if not segments:
        return timeline

    # ── Cảnh đầu ─────────────────────────────────────────
    windows = _pick_windows(
        duration, cfg["scenes"], cfg["min_len"], cfg["max_len"],
        _rng_for(cfg["seed"], idx, "hook"), idx, total,
    )
    hook_segments = [{"asset_id": asset["id"], "start": st, "end": en}
                     for st, en in windows]

    # Thay các cảnh đầu, nhưng luôn chừa lại ít nhất một cảnh thân. Timeline chỉ
    # có mỗi video B thì không xoá gì cả, chỉ chèn hook vào trước — người dùng
    # không bao giờ mất trắng phần thân vì bật nhầm số cảnh hook.
    replace = max(0, min(cfg["scenes"], len(segments) - 1))
    rest = segments[replace:]

    # ── Phần thân ────────────────────────────────────────
    body = _body_cfg(hook)
    if body["enabled"] and rest:
        b_asset = _body_asset(hook, segments, replace, assets)
        b_dur = float(b_asset.get("duration") or 0) if b_asset else 0.0
        if b_asset and b_asset.get("kind") != "audio" and b_dur >= body["min_len"]:
            st, en = _pick_windows(
                b_dur, 1, body["min_len"], body["max_len"],
                _rng_for(cfg["seed"], idx, "body"), idx, total,
            )[0]
            # Giữ lại mọi thiết lập khác của cảnh thân (đảo ngược, v.v.) —
            # chỉ đổi clip nguồn và đoạn cắt.
            rest = [{**rest[0], "asset_id": b_asset["id"],
                     "start": st, "end": en}] + rest[1:]

    new_segments = hook_segments + rest

    # Mỗi lần chèn thêm một cảnh là thêm một mối nối, cần thêm một chuyển cảnh.
    fill = transitions[0] if transitions else {"type": "fade", "duration": 0.5}
    added = len(new_segments) - len(segments)
    new_transitions = ([dict(fill) for _ in range(added)] + transitions) if added > 0 else transitions

    out = dict(timeline)
    out["segments"] = new_segments
    out["transitions"] = new_transitions
    return out


def _timeline_duration(timeline: dict) -> float:
    """Thời lượng thành phẩm — tính đúng như lúc ghép, kể cả phần chuyển cảnh nuốt."""
    segments = timeline.get("segments") or []
    transitions = timeline.get("transitions") or []
    if not segments:
        return 0.0

    lengths = [max(0.1, float(s.get("end", 0) or 0) - float(s.get("start", 0) or 0))
               for s in segments]
    total = lengths[0]
    for i in range(1, len(lengths)):
        t = transitions[i - 1] if i - 1 < len(transitions) else {}
        max_trans = max(0.0, min(total, lengths[i]) - 0.05)
        dur = _clamp(float(t.get("duration", 0.5) or 0.5), 0.05, 2.5)
        dur = min(dur, max_trans)
        if t.get("type") == "none" or dur <= 0.05:
            total += lengths[i]
        else:
            total += lengths[i] - dur
    return round(total, 2)


def hook_plan(timeline: dict, hook: dict, assets: dict[int, dict],
              count: int) -> list[dict]:
    """Kế hoạch ghép của từng biến thể — dùng cho bảng xem trước.

    Đúng bằng cái mà `build_hook_timeline` sẽ dựng lúc render, nhờ cùng `seed`.
    """
    count = int(_clamp(count, 1, 200))
    plans: list[dict] = []
    base_segments = timeline.get("segments") or []
    hook_scenes = _hook_cfg(hook)["scenes"] if hook.get("enabled") else 0

    for i in range(count):
        tl = build_hook_timeline(timeline, hook, assets, i, count)
        rows = []
        for pos, seg in enumerate(tl.get("segments") or []):
            a = assets.get(int(seg.get("asset_id") or 0)) or {}
            start = float(seg.get("start", 0) or 0)
            end = float(seg.get("end", 0) or 0)
            if pos < hook_scenes:
                role = "hook"
            elif pos == hook_scenes and _body_cfg(hook)["enabled"]:
                role = "than"
            else:
                role = "codinh"
            rows.append({
                "reverse": bool(seg.get("reverse")),
                "asset_id": a.get("id"),
                "name": a.get("name", "(clip đã xoá)"),
                "source_duration": round(float(a.get("duration") or 0), 2),
                "start": round(start, 2),
                "end": round(end, 2),
                "length": round(max(0.0, end - start), 2),
                "role": role,
            })
        plans.append({
            "idx": i + 1,
            "segments": rows,
            "duration": _timeline_duration(tl),
            "changed": len(tl.get("segments") or []) != len(base_segments)
                       or tl is not timeline,
        })
    return plans


def hook_is_usable(timeline: dict, hook: dict, assets: dict[int, dict]) -> str:
    """Lý do ghép ngẫu nhiên không dùng được, chuỗi rỗng nghĩa là dùng được."""
    if not hook or not hook.get("enabled"):
        return "Chưa bật"

    asset = assets.get(int(hook.get("asset_id") or 0))
    if not asset:
        return "Chưa chọn clip nguồn cho cảnh đầu, hoặc clip đó đã bị xoá."
    if asset.get("kind") == "audio":
        return "Clip nguồn của cảnh đầu đang là file nhạc. Hãy chọn một clip video."

    cfg = _hook_cfg(hook)
    duration = float(asset.get("duration") or 0)
    if duration < cfg["scenes"] * cfg["min_len"]:
        return (f"Clip nguồn chỉ dài {duration:.1f}s, không cắt đủ {cfg['scenes']} cảnh "
                f"mỗi cảnh tối thiểu {cfg['min_len']:.0f}s. Hãy chọn clip dài hơn hoặc "
                f"giảm độ dài cảnh đầu.")

    segments = timeline.get("segments") or []
    if not segments:
        return "Timeline chưa có cảnh nào."

    body = _body_cfg(hook)
    if body["enabled"]:
        replace = max(0, min(cfg["scenes"], len(segments) - 1))
        b_asset = _body_asset(hook, segments, replace, assets)
        if not b_asset:
            return "Chưa chọn được clip cho phần thân."
        if b_asset.get("kind") == "audio":
            return "Clip của phần thân đang là file nhạc. Hãy chọn một clip video."
        b_dur = float(b_asset.get("duration") or 0)
        if b_dur < body["min_len"]:
            return (f"Clip thân \"{b_asset.get('name', '')}\" chỉ dài {b_dur:.1f}s, "
                    f"không cắt được đoạn {body['min_len']:.0f}s. Giảm độ dài phần thân "
                    f"hoặc chọn clip dài hơn.")
    return ""


async def _compose_to(timeline: dict, assets: dict[int, dict], out_path: Path) -> dict:
    """Ghép một timeline ra đúng một file — dùng cho base riêng của từng biến thể."""
    temp_files: list[Path] = []
    try:
        args, expected = build_compose_command(timeline, assets, out_path, temp_files)
    except ValueError as e:
        return {"error": str(e)}

    problem = check_graph_filters(args)
    if problem:
        return {"error": problem}

    result = await run_ffmpeg(args)
    for tf in temp_files:
        _try_delete(tf)

    if result.returncode != 0 or not out_path.exists():
        return {"error": _ffmpeg_error(result.stderr or "")}
    return {"duration": expected}


async def preview_hook_plan(project_id: int, timeline: dict | None, count: int) -> dict:
    """Kế hoạch ghép của N biến thể — để xem trước, không render gì cả."""
    project = await get_project(project_id)
    if not project:
        return {"error": "Không tìm thấy dự án"}

    tl = timeline if timeline is not None else project["timeline"]
    hook = tl.get("hook") or {}
    assets = {a["id"]: a for a in await list_assets()}

    why = hook_is_usable(tl, hook, assets)
    if why and why != "Chưa bật":
        return {"error": why}
    if why == "Chưa bật":
        return {"error": "Chưa bật ghép ngẫu nhiên."}

    return {"variants": hook_plan(tl, hook, assets, count)}


async def preview_hook_variant(project_id: int, timeline: dict | None,
                               idx: int, count: int) -> dict:
    """Ghép thật đúng một biến thể để xem trước bằng mắt.

    Dùng chung `seed` với lúc render nên bản xem ở đây chính là bản sẽ ra.
    """
    project = await get_project(project_id)
    if not project:
        return {"error": "Không tìm thấy dự án"}

    tl = timeline if timeline is not None else project["timeline"]
    hook = tl.get("hook") or {}
    assets = {a["id"]: a for a in await list_assets()}

    why = hook_is_usable(tl, hook, assets)
    if why:
        return {"error": why if why != "Chưa bật" else "Chưa bật ghép ngẫu nhiên."}

    count = int(_clamp(count, 1, 200))
    idx = int(_clamp(idx, 1, count)) - 1
    hook_tl = build_hook_timeline(tl, hook, assets, idx, count)

    # Mỗi dự án chỉ giữ một file xem thử — xem bản khác thì ghi đè lên, không
    # để lại một đống file nặng trong thư mục.
    for old in STUDIO_BASE_DIR.glob(f"hookprev_{project_id}_*.mp4"):
        _try_delete(old)

    out = STUDIO_BASE_DIR / f"hookprev_{project_id}_{uuid.uuid4().hex[:8]}.mp4"
    made = await _compose_to(hook_tl, assets, out)
    if made.get("error"):
        return {"error": made["error"]}

    return {
        "idx": idx + 1,
        "url": f"/media/studio/base/{out.name}",
        "duration": made["duration"],
        "segments": hook_plan(tl, hook, assets, count)[idx]["segments"],
    }


async def start_batch_render(
    project_id: int,
    count: int,
    look_ids: list[str],
    music_asset_ids: list[int],
    keep_original_audio: bool = False,
    music_volume: float = 1.0,
) -> dict:
    """Khởi tạo job render N biến thể từ video base của dự án."""
    import asyncio

    project = await get_project(project_id)
    if not project:
        return {"error": "Không tìm thấy dự án"}

    base_path = Path(project.get("base_filepath") or "")
    if not base_path.exists():
        return {"error": "Chưa ghép video base. Bấm 'Ghép & Xem trước' trước khi render."}

    count = int(_clamp(count, 1, 200))

    job_id = uuid.uuid4().hex[:12]
    job = {
        "job_id": job_id,
        "project_id": project_id,
        "project_name": project["name"],
        "status": "pending",
        "total": count,
        "completed": 0,
        "failed": 0,
        "renders": [],
        "error": "",
        "started_at": datetime.now().isoformat(),
        "finished_at": "",
    }
    _batch_jobs[job_id] = job

    asyncio.create_task(_run_batch_render(
        job, project, base_path, count, look_ids, music_asset_ids,
        keep_original_audio, music_volume,
    ))
    return job


async def _run_batch_render(
    job: dict,
    project: dict,
    base_path: Path,
    count: int,
    look_ids: list[str],
    music_asset_ids: list[int],
    keep_original_audio: bool,
    music_volume: float,
) -> None:
    job["status"] = "running"

    looks = [lid for lid in (look_ids or []) if lid in _LOOKS_BY_ID] or ["original"]

    music_pool: list[dict] = []
    for mid in music_asset_ids or []:
        asset = await get_asset(int(mid))
        if asset and asset["kind"] == "audio":
            music_pool.append(asset)

    timeline = project.get("timeline") or {}
    canvas = timeline.get("canvas") or {}
    width = int(canvas.get("width", 1080))
    height = int(canvas.get("height", 1920))
    fps = int(canvas.get("fps", 30))
    base_duration = float(project.get("base_duration") or 0) or 15.0

    out_dir = STUDIO_RENDERS_DIR / job["job_id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    base_name = _sanitize(project["name"])

    db = await get_db()
    rng = random.Random(random.SystemRandom().randint(0, 2**32))

    # Hook ngẫu nhiên: mỗi biến thể ghép lại từ đầu với một mở đầu khác nhau,
    # thay vì cùng dùng chung một video base như thường lệ.
    hook = timeline.get("hook") or {}
    assets: dict[int, dict] = {}
    use_hook = False
    if hook.get("enabled"):
        assets = {a["id"]: a for a in await list_assets()}
        why = hook_is_usable(timeline, hook, assets)
        use_hook = not why
        if why:
            log.warning("Hook ngẫu nhiên bị bỏ qua: %s", why)
            job["error"] = f"Hook ngẫu nhiên bị bỏ qua — {why}"

    # Lý do thất bại của biến thể đầu tiên — để báo đúng nguyên nhân thay vì
    # câu chung chung "kiểm tra log", thứ mà nhân sự không mở bao giờ.
    filter_problem = ""

    for i in range(count):
        idx = i + 1
        await ws_manager.broadcast({
            "type": "studio_batch",
            "job_id": job["job_id"],
            "status": "processing",
            "current": idx,
            "total": count,
            "message": f"Đang render biến thể {idx}/{count}...",
        })

        look_id = looks[i % len(looks)]
        music = music_pool[i % len(music_pool)] if music_pool else None
        out_file = out_dir / f"{base_name}_v{idx:03d}.mp4"

        # Mỗi biến thể có mở đầu riêng thì phải ghép lại từ các clip gốc, không
        # dùng chung video base được. Số lần mã hoá vẫn là hai như trước (ghép
        # rồi mới tạo biến thể), nên chất lượng không đổi — chỉ tốn thêm thời gian.
        variant_base = base_path
        variant_duration = base_duration
        hook_temp: Path | None = None
        hook_info: dict | None = None
        if use_hook:
            hook_tl = build_hook_timeline(timeline, hook, assets, i, count)
            hook_temp = TEMP_DIR / f"hookbase_{job['job_id']}_{idx:03d}.mp4"
            made = await _compose_to(hook_tl, assets, hook_temp)
            if made.get("error"):
                log.error("Biến thể %s: không ghép được hook — %s", idx, made["error"])
                filter_problem = filter_problem or made["error"]
                job["failed"] += 1
                _try_delete(hook_temp)
                continue
            variant_base = hook_temp
            variant_duration = made["duration"]
            hook_info = {
                "scenes": [{"start": sg["start"], "end": sg["end"]}
                           for sg in hook_tl["segments"][:int(hook.get("scenes", 1) or 1)]],
            }

        args, recipe = _build_variant_command(
            variant_base, out_file, look_id, music, rng, width, height, fps,
            variant_duration, music_volume, keep_original_audio,
            audio_tune=(timeline.get("audio") or {}).get("tune"),
        )
        if hook_info:
            recipe["hook"] = hook_info
        recipe["index"] = idx

        problem = check_graph_filters(args)
        if problem:
            log.error("Biến thể %s không render được: %s", idx, problem)
            filter_problem = problem
            job["failed"] += 1
            continue

        result = await run_ffmpeg(args)

        if hook_temp:
            # Base riêng của biến thể này đã dùng xong — xoá ngay, không thì
            # render 100 bản sẽ để lại 100 file rác nặng hàng GB trong data/temp.
            _try_delete(hook_temp)

        if result.returncode != 0 or not out_file.exists():
            log.warning("Biến thể %s lỗi: %s", idx, (result.stderr or "")[-500:])
            if not filter_problem:
                filter_problem = _ffmpeg_error(result.stderr or "")
            job["failed"] += 1
            continue

        try:
            probe = await get_video_info(out_file)
        except (FileNotFoundError, OSError):
            probe = {}

        # Ghi vào bảng variants để Content Studio đăng lên Fanpage như bình thường
        variant_db_id = None
        try:
            cursor = await db.execute(
                """INSERT INTO variants
                       (video_id, filename, filepath, profile, transforms,
                        filesize, duration, width, height, status)
                   VALUES (?, ?, ?, 'studio', ?, ?, ?, ?, ?, 'ready')""",
                (
                    f"studio_{job['project_id']}",
                    out_file.name,
                    str(out_file),
                    json.dumps(recipe, ensure_ascii=False),
                    out_file.stat().st_size,
                    probe.get("duration", variant_duration),
                    probe.get("width", width),
                    probe.get("height", height),
                ),
            )
            await db.commit()
            variant_db_id = cursor.lastrowid
        except Exception as e:
            log.warning("Không lưu được variant vào DB: %s", e)

        render_db_id = None
        try:
            cursor = await db.execute(
                """INSERT INTO studio_renders
                       (project_id, job_id, variant_id, idx, filename, filepath,
                        recipe, filesize, duration)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (job["project_id"], job["job_id"], variant_db_id, idx,
                 out_file.name, str(out_file), json.dumps(recipe, ensure_ascii=False),
                 out_file.stat().st_size, probe.get("duration", variant_duration)),
            )
            await db.commit()
            render_db_id = cursor.lastrowid
        except Exception as e:
            log.warning("Không lưu được studio_render: %s", e)

        render_entry = {
            "id": render_db_id,
            "idx": idx,
            "variant_id": variant_db_id,
            "filename": out_file.name,
            "filepath": str(out_file),
            "media_url": f"/media/studio/renders/{job['job_id']}/{out_file.name}",
            "recipe": recipe,
            "filesize": out_file.stat().st_size,
            "duration": probe.get("duration", variant_duration),
        }
        job["renders"].append(render_entry)
        job["completed"] += 1

        await ws_manager.broadcast({
            "type": "studio_batch",
            "job_id": job["job_id"],
            "status": "variant_done",
            "current": idx,
            "total": count,
            "render": render_entry,
        })

    job["status"] = "completed" if job["completed"] else "failed"
    job["finished_at"] = datetime.now().isoformat()
    if not job["completed"]:
        job["error"] = filter_problem or (
            "Không render được biến thể nào. Kiểm tra log tại data/app.log")

    await ws_manager.broadcast({
        "type": "studio_batch",
        "job_id": job["job_id"],
        "status": job["status"],
        "current": job["completed"],
        "total": count,
        "message": f"Xong! {job['completed']}/{count} biến thể.",
    })


def _export_names(renders: list[dict], project_name: str) -> list[tuple[dict, str]]:
    """Đánh số lại tên file liên tục cho một lượt xuất.

    Mỗi lần render lại đều đánh số từ v001, nên một dự án render nhiều lượt sẽ có
    nhiều file trùng tên (chúng nằm ở thư mục job khác nhau nên không sao). Nhưng khi
    gộp tất cả vào MỘT thư mục hay MỘT file zip thì chúng ghi đè lên nhau và mất bản.
    Vì vậy khi xuất phải đánh số lại theo thứ tự trong danh sách.
    """
    pairs: list[tuple[dict, str]] = []
    for position, r in enumerate(renders, start=1):
        ext = Path(r["filepath"]).suffix or ".mp4"
        pairs.append((r, f"{project_name}_v{position:03d}{ext}"))
    return pairs


async def _project_export_name(project_id: int | None) -> str:
    if project_id:
        project = await get_project(project_id)
        if project:
            return _sanitize(project["name"], 40)
    return "VideoStudio"


async def build_audio_preview(
    asset_id: int,
    start: float = 0.0,
    duration: float = 10.0,
    tune: dict | None = None,
    raw: bool = False,
) -> dict:
    """Cắt một đoạn tiếng của clip để nghe thử trước khi ghép.

    `raw=True` trả về tiếng gốc chưa chỉnh, dùng để so sánh trước/sau.
    """
    asset = await get_asset(asset_id)
    if not asset:
        return {"error": "Không tìm thấy clip"}
    if not asset.get("has_audio"):
        return {"error": "Clip này không có tiếng"}

    src = Path(asset["filepath"])
    if not src.exists():
        return {"error": "File clip không còn trên ổ đĩa"}

    duration = _clamp(duration, 2.0, 30.0)
    start = max(0.0, start)

    out_path = TEMP_DIR / f"preview_{uuid.uuid4().hex[:8]}.mp3"
    args = ["-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(src)]

    filters = [] if raw else build_audio_tune_filters(tune)
    if filters:
        args += ["-af", ",".join(filters)]

    args += ["-vn", "-c:a", "libmp3lame", "-b:a", "160k", "-ar", "44100", str(out_path)]

    result = await run_ffmpeg(args)
    if result.returncode != 0 or not out_path.exists():
        out_path.unlink(missing_ok=True)
        return {"error": _ffmpeg_error(result.stderr or "")}

    return {"path": str(out_path)}


async def get_render(render_id: int) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM studio_renders WHERE id = ?", (render_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def export_renders(
    export_path: str,
    job_id: str | None = None,
    project_id: int | None = None,
    create_subfolder: bool = True,
) -> dict:
    """Chép các biến thể đã render sang thư mục người dùng chọn."""
    renders = await list_renders(project_id, job_id)
    renders = [r for r in renders if Path(r["filepath"]).exists()]
    if not renders:
        return {"error": "Không có biến thể nào để xuất"}

    project_name = await _project_export_name(project_id)

    target = Path(export_path)
    if create_subfolder:
        # Gom theo tên dự án + ngày để không lẫn với lần xuất trước
        target = target / f"{project_name}_{datetime.now():%d-%m-%Y_%Hh%M}"

    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return {"error": f"Không tạo được thư mục: {e}"}

    exported: list[str] = []
    failed: list[str] = []
    total_bytes = 0

    for r, name in _export_names(renders, project_name):
        src = Path(r["filepath"])
        dest = target / name
        try:
            shutil.copy2(str(src), str(dest))
            exported.append(name)
            total_bytes += dest.stat().st_size
        except OSError as e:
            log.error("Xuất %s thất bại: %s", name, e)
            failed.append(name)

    if not exported:
        return {"error": "Không chép được file nào. Kiểm tra quyền ghi vào thư mục này."}

    return {
        "success": True,
        "exported_count": len(exported),
        "failed_count": len(failed),
        "export_path": str(target),
        "total_bytes": total_bytes,
        "files": exported,
    }


async def build_renders_zip(job_id: str | None = None,
                            project_id: int | None = None) -> dict:
    """Nén các biến thể thành một file ZIP tạm để tải về."""
    import asyncio
    import zipfile

    renders = await list_renders(project_id, job_id)
    renders = [r for r in renders if Path(r["filepath"]).exists()]
    if not renders:
        return {"error": "Không có biến thể nào để tải"}

    project_name = await _project_export_name(project_id)
    filename = f"{project_name}_{datetime.now():%d-%m-%Y_%Hh%M}.zip"
    zip_path = TEMP_DIR / f"export_{uuid.uuid4().hex[:8]}.zip"
    named = _export_names(renders, project_name)

    def _write_zip() -> None:
        # ZIP_STORED: video đã nén sẵn, nén lại chỉ tốn thời gian mà không giảm dung lượng
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
            for r, name in named:
                zf.write(r["filepath"], arcname=name)

    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, _write_zip)
    except OSError as e:
        zip_path.unlink(missing_ok=True)
        log.error("Tạo ZIP thất bại: %s", e)
        return {"error": f"Không tạo được file ZIP: {e}"}

    return {
        "zip_path": str(zip_path),
        "filename": filename,
        "count": len(renders),
    }


async def list_renders(project_id: int | None = None, job_id: str | None = None) -> list[dict]:
    db = await get_db()
    query = "SELECT * FROM studio_renders WHERE 1=1"
    params: list = []
    if project_id:
        query += " AND project_id = ?"
        params.append(project_id)
    if job_id:
        query += " AND job_id = ?"
        params.append(job_id)
    query += " ORDER BY idx ASC"

    cursor = await db.execute(query, params)
    out = []
    for row in await cursor.fetchall():
        d = dict(row)
        try:
            d["recipe"] = json.loads(d.get("recipe") or "{}")
        except json.JSONDecodeError:
            d["recipe"] = {}
        d["media_url"] = f"/media/studio/renders/{d['job_id']}/{d['filename']}"
        out.append(d)
    return out
