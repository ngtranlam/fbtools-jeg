from __future__ import annotations

import hashlib
import re

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from backend.config import DOWNLOADS_DIR, STUDIO_DIR, VARIANTS_DIR
from backend.routes import download, spoof, check, metadata, accounts, pages, posts, settings, ai, spy, inbox, channels
from backend.routes import pinterest_browser, studio
from backend.utils.websocket import ws_manager

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

# File logging setup — persist to data/app.log for debugging
_log_dir = BASE_DIR / "data"
_log_dir.mkdir(parents=True, exist_ok=True)
_log_fmt = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=_log_fmt, handlers=[
    logging.StreamHandler(),
    logging.FileHandler(str(_log_dir / "app.log"), encoding="utf-8"),
])
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    # Startup
    from backend.database import init_db
    await init_db()
    log.info("Database initialized")

    from backend.services.scheduler import start_scheduler
    await start_scheduler()
    log.info("Scheduler started")

    yield

    # Shutdown
    from backend.services.scheduler import stop_scheduler
    stop_scheduler()
    log.info("Scheduler stopped")


app = FastAPI(
    title="MocLan Viral Hub",
    description="Hệ thống quản lý 100+ Fanpage Facebook — Spoof, Đăng Reels, Theo dõi Viral",
    version="3.5.0",
    lifespan=lifespan,
)



# Existing routes
app.include_router(download.router)
app.include_router(spoof.router)
app.include_router(check.router)
app.include_router(metadata.router)

# New routes
app.include_router(accounts.router)
app.include_router(pages.router)
app.include_router(posts.router)
app.include_router(settings.router)
app.include_router(ai.router)
app.include_router(spy.router)
app.include_router(inbox.router)
app.include_router(channels.router)
app.include_router(pinterest_browser.router)
app.include_router(studio.router)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
app.mount("/media/downloads", StaticFiles(directory=str(DOWNLOADS_DIR)), name="downloads")
app.mount("/media/variants", StaticFiles(directory=str(VARIANTS_DIR)), name="variants")
app.mount("/media/studio", StaticFiles(directory=str(STUDIO_DIR)), name="studio")


#: Số `?v=` trong index.html trước đây gõ tay, và lần nào sửa JS/CSS cũng quên
#: tăng. Hậu quả chỉ lộ ra trên máy ĐÃ CÀI TỪ TRƯỚC: trình duyệt thấy y hệt
#: đường dẫn cũ nên dùng lại bản trong bộ nhớ đệm, máy chủ chạy mã mới còn giao
#: diện vẫn là mã cũ — nửa mới nửa cũ, hỏng những chỗ không ai đoán ra.
#: Nay máy chủ tự thay số đó bằng vân tay nội dung file, sửa file nào là số của
#: file ấy đổi theo, không còn phụ thuộc việc nhớ hay quên.
_ASSET_VER_RE = re.compile(r'(?P<attr>href|src)="(?P<path>/static/[^"?]+)(\?v=[^"]*)?"')
_asset_ver_cache: dict[str, tuple[float, int, str]] = {}


def _asset_version(rel_path: str) -> str:
    """Vân tay nội dung của một file tĩnh, dùng làm số `?v=`."""
    f = FRONTEND_DIR / rel_path.removeprefix("/static/")
    try:
        st = f.stat()
    except OSError:
        return "0"

    cached = _asset_ver_cache.get(rel_path)
    if cached and cached[0] == st.st_mtime and cached[1] == st.st_size:
        return cached[2]

    try:
        digest = hashlib.sha1(f.read_bytes()).hexdigest()[:10]
    except OSError:
        return "0"

    _asset_ver_cache[rel_path] = (st.st_mtime, st.st_size, digest)
    return digest


def _stamp_assets(html: str) -> str:
    return _ASSET_VER_RE.sub(
        lambda m: f'{m["attr"]}="{m["path"]}?v={_asset_version(m["path"])}"',
        html,
    )


@app.get("/")
async def serve_index():
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(
        _stamp_assets(html),
        # Bản thân index.html không được nằm lại trong bộ nhớ đệm, nếu không
        # trình duyệt sẽ không bao giờ thấy danh sách phiên bản mới.
        headers={"Cache-Control": "no-store, must-revalidate"},
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


#: Đổi mỗi lần phát hành. Giao diện đối chiếu với số này để phát hiện trường hợp
#: đã cập nhật mã nguồn nhưng chưa khởi động lại tool (máy chủ vẫn chạy mã cũ
#: trong bộ nhớ, còn trình duyệt đã tải giao diện mới).
BUILD = "2026.09.09"


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "version": "3.5.0",
        "build": BUILD,
        "app": "MocLan Viral Hub",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
