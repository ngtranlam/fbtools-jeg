"""SQLite database manager with auto-migration."""

from __future__ import annotations

import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "moclan.db"

_SCHEMA = """
-- Tài khoản Facebook cá nhân
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    fb_user_id TEXT DEFAULT '',
    access_token TEXT NOT NULL,
    fb_app_id TEXT DEFAULT '',
    fb_app_secret TEXT DEFAULT '',
    token_expires_at TEXT DEFAULT '',
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Fanpages được quản lý
CREATE TABLE IF NOT EXISTS pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    fb_page_id TEXT NOT NULL UNIQUE,
    page_name TEXT NOT NULL,
    page_access_token TEXT NOT NULL,
    category TEXT DEFAULT '',
    avatar_url TEXT DEFAULT '',
    store_url TEXT DEFAULT '',
    comment_templates TEXT DEFAULT '[]',
    followers_count INTEGER DEFAULT 0,
    total_views INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

-- Video gốc đã download
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_url TEXT DEFAULT '',
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    platform TEXT DEFAULT 'unknown',
    duration REAL DEFAULT 0,
    width INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0,
    filesize INTEGER DEFAULT 0,
    thumbnail TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now'))
);

-- Biến thể video đã spoof
CREATE TABLE IF NOT EXISTS variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    profile TEXT DEFAULT 'medium',
    transforms TEXT DEFAULT '[]',
    filesize INTEGER DEFAULT 0,
    duration REAL DEFAULT 0,
    width INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0,
    status TEXT DEFAULT 'ready',
    created_at TEXT DEFAULT (datetime('now'))
);

-- Bài đăng trên Facebook
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id INTEGER NOT NULL,
    variant_id INTEGER,
    fb_post_id TEXT DEFAULT '',
    post_type TEXT DEFAULT 'reel',
    caption TEXT DEFAULT '',
    filepath TEXT DEFAULT '',
    first_comment TEXT DEFAULT '',
    comment_image_url TEXT DEFAULT '',
    comment_status TEXT DEFAULT '',
    status TEXT DEFAULT 'draft',
    scheduled_at TEXT DEFAULT '',
    posted_at TEXT DEFAULT '',
    views_count INTEGER DEFAULT 0,
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    shares_count INTEGER DEFAULT 0,
    viral_level TEXT DEFAULT 'none',
    last_checked_at TEXT DEFAULT '',
    error_message TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES variants(id) ON DELETE SET NULL
);

-- Lịch sử alert viral
CREATE TABLE IF NOT EXISTS viral_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    level TEXT NOT NULL,
    views_at_alert INTEGER DEFAULT 0,
    comment_sent INTEGER DEFAULT 0,
    telegram_sent INTEGER DEFAULT 0,
    alerted_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
);

-- Lịch sử metrics page (sync mỗi giờ)
CREATE TABLE IF NOT EXISTS page_metrics_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id INTEGER NOT NULL,
    followers_count INTEGER DEFAULT 0,
    daily_views INTEGER DEFAULT 0,
    daily_reach INTEGER DEFAULT 0,
    total_posts INTEGER DEFAULT 0,
    top_video_id TEXT DEFAULT '',
    top_video_views INTEGER DEFAULT 0,
    synced_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
);

-- Spy Channels (TikTok / YouTube)
CREATE TABLE IF NOT EXISTS spy_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL DEFAULT 'tiktok',
    channel_url TEXT NOT NULL UNIQUE,
    channel_id TEXT DEFAULT '',
    channel_name TEXT NOT NULL,
    avatar_url TEXT DEFAULT '',
    followers_count INTEGER DEFAULT 0,
    videos_count INTEGER DEFAULT 0,
    notes TEXT DEFAULT '',
    status TEXT DEFAULT 'active',
    last_synced_at TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now'))
);

-- Spy Videos (fetched from spy channels)
CREATE TABLE IF NOT EXISTS spy_videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER NOT NULL,
    video_url TEXT NOT NULL UNIQUE,
    video_id TEXT DEFAULT '',
    title TEXT DEFAULT '',
    description TEXT DEFAULT '',
    thumbnail_url TEXT DEFAULT '',
    views_count INTEGER DEFAULT 0,
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    shares_count INTEGER DEFAULT 0,
    duration REAL DEFAULT 0,
    published_at TEXT DEFAULT '',
    reupped INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (channel_id) REFERENCES spy_channels(id) ON DELETE CASCADE
);

-- Unified Inbox Comments
CREATE TABLE IF NOT EXISTS inbox_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id INTEGER NOT NULL,
    fb_post_id TEXT NOT NULL,
    fb_comment_id TEXT NOT NULL UNIQUE,
    commenter_name TEXT DEFAULT '',
    commenter_id TEXT DEFAULT '',
    message TEXT DEFAULT '',
    replied INTEGER DEFAULT 0,
    reply_message TEXT DEFAULT '',
    replied_at TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
);

-- Cài đặt hệ thống (key-value)
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pages_account ON pages(account_id);
CREATE INDEX IF NOT EXISTS idx_posts_page ON posts(page_id);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_viral ON posts(viral_level);
CREATE INDEX IF NOT EXISTS idx_variants_video ON variants(video_id);
CREATE INDEX IF NOT EXISTS idx_viral_alerts_post ON viral_alerts(post_id);
CREATE INDEX IF NOT EXISTS idx_page_metrics_page ON page_metrics_history(page_id);
CREATE INDEX IF NOT EXISTS idx_page_metrics_time ON page_metrics_history(synced_at);
CREATE INDEX IF NOT EXISTS idx_spy_channels_platform ON spy_channels(platform);
CREATE INDEX IF NOT EXISTS idx_spy_videos_channel ON spy_videos(channel_id);
CREATE INDEX IF NOT EXISTS idx_spy_videos_views ON spy_videos(views_count);
CREATE INDEX IF NOT EXISTS idx_inbox_page ON inbox_comments(page_id);
CREATE INDEX IF NOT EXISTS idx_inbox_replied ON inbox_comments(replied);

-- Multi-platform channels (Pinterest, YouTube)
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    channel_name TEXT NOT NULL,
    channel_id TEXT DEFAULT '',
    avatar_url TEXT DEFAULT '',
    credentials TEXT DEFAULT '{}',
    extra_data TEXT DEFAULT '{}',
    followers_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_channels_platform ON channels(platform);
CREATE INDEX IF NOT EXISTS idx_channels_status ON channels(status);

-- ══ Video Studio ═══════════════════════════════════════════
-- Nguồn media dùng để ghép (video clip / nhạc nền)
CREATE TABLE IF NOT EXISTS studio_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL DEFAULT 'video',      -- video | audio
    name TEXT NOT NULL,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    duration REAL DEFAULT 0,
    width INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0,
    fps REAL DEFAULT 30,
    filesize INTEGER DEFAULT 0,
    has_audio INTEGER DEFAULT 1,
    source TEXT DEFAULT 'upload',            -- upload | library | download
    created_at TEXT DEFAULT (datetime('now'))
);

-- Dự án ghép video (timeline dạng JSON)
CREATE TABLE IF NOT EXISTS studio_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL DEFAULT 'Dự án mới',
    timeline TEXT DEFAULT '{}',
    base_filename TEXT DEFAULT '',
    base_filepath TEXT DEFAULT '',
    base_duration REAL DEFAULT 0,
    status TEXT DEFAULT 'draft',             -- draft | composed | rendering
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Các bản render hàng loạt từ 1 dự án
CREATE TABLE IF NOT EXISTS studio_renders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    job_id TEXT DEFAULT '',
    variant_id INTEGER,
    idx INTEGER DEFAULT 0,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    recipe TEXT DEFAULT '{}',
    filesize INTEGER DEFAULT 0,
    duration REAL DEFAULT 0,
    status TEXT DEFAULT 'ready',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES studio_projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_studio_assets_kind ON studio_assets(kind);
CREATE INDEX IF NOT EXISTS idx_studio_renders_project ON studio_renders(project_id);
CREATE INDEX IF NOT EXISTS idx_studio_renders_job ON studio_renders(job_id);
"""

_DEFAULT_SETTINGS = {
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "viral_threshold_catching": "10000",
    "viral_threshold_viral": "100000",
    "viral_threshold_super_viral": "1000000",
    "monitor_interval_minutes": "30",
    "auto_comment_enabled": "false",
    "auto_comment_delay_min": "30",
    "auto_comment_delay_max": "120",
    "auto_cleanup_enabled": "true",
    "auto_cleanup_source_after_spoof": "true",
    "auto_cleanup_variant_days": "7",
    "daily_report_enabled": "true",
    "daily_report_hour": "8",
    "sync_interval_minutes": "60",
    "growth_alert_followers_threshold": "50",
    "openai_api_key": "",
    # Spy: tự động cập nhật chỉ số kênh đối thủ chạy nền
    "spy_auto_sync_enabled": "true",
    "spy_sync_interval_minutes": "180",
    "spy_alert_views_delta": "5000",
}


_shared_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _shared_db
    if _shared_db is None:
        _shared_db = await aiosqlite.connect(str(DB_PATH), timeout=30)
        _shared_db.row_factory = aiosqlite.Row
        await _shared_db.execute("PRAGMA journal_mode=WAL")
        await _shared_db.execute("PRAGMA foreign_keys=ON")
        await _shared_db.execute("PRAGMA busy_timeout=30000")
    return _shared_db


async def close_db() -> None:
    global _shared_db
    if _shared_db:
        await _shared_db.close()
        _shared_db = None


async def init_db() -> None:
    """Create tables and seed default settings."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = await get_db()
    await db.executescript(_SCHEMA)

    # Auto-migrate: add columns if missing
    await _migrate(db)

    # Seed default settings
    for key, value in _DEFAULT_SETTINGS.items():
        await db.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
    await db.commit()


async def _migrate(db: aiosqlite.Connection) -> None:
    """Add missing columns to existing tables."""
    migrations = [
        ("accounts", "token_type",
         "ALTER TABLE accounts ADD COLUMN token_type TEXT DEFAULT 'user'"),
        ("pages", "total_views", "ALTER TABLE pages ADD COLUMN total_views INTEGER DEFAULT 0"),
        ("posts", "filepath", "ALTER TABLE posts ADD COLUMN filepath TEXT DEFAULT ''"),
        ("posts", "first_comment", "ALTER TABLE posts ADD COLUMN first_comment TEXT DEFAULT ''"),
        ("posts", "comment_status", "ALTER TABLE posts ADD COLUMN comment_status TEXT DEFAULT ''"),
        # Multi-platform support
        ("posts", "platform", "ALTER TABLE posts ADD COLUMN platform TEXT DEFAULT 'facebook'"),
        ("posts", "channel_id", "ALTER TABLE posts ADD COLUMN channel_id INTEGER DEFAULT NULL"),
        ("posts", "platform_post_id", "ALTER TABLE posts ADD COLUMN platform_post_id TEXT DEFAULT ''"),
        ("posts", "extra_data", "ALTER TABLE posts ADD COLUMN extra_data TEXT DEFAULT '{}'"),
        # Comment with image support
        ("posts", "comment_image_url", "ALTER TABLE posts ADD COLUMN comment_image_url TEXT DEFAULT ''"),
        # Spy: growth tracking between syncs
        ("spy_videos", "prev_views_count", "ALTER TABLE spy_videos ADD COLUMN prev_views_count INTEGER DEFAULT 0"),
        ("spy_videos", "views_delta", "ALTER TABLE spy_videos ADD COLUMN views_delta INTEGER DEFAULT 0"),
        ("spy_videos", "likes_delta", "ALTER TABLE spy_videos ADD COLUMN likes_delta INTEGER DEFAULT 0"),
        ("spy_videos", "engagement_rate", "ALTER TABLE spy_videos ADD COLUMN engagement_rate REAL DEFAULT 0"),
        ("spy_videos", "is_new", "ALTER TABLE spy_videos ADD COLUMN is_new INTEGER DEFAULT 0"),
        ("spy_videos", "first_seen_at", "ALTER TABLE spy_videos ADD COLUMN first_seen_at TEXT DEFAULT ''"),
        ("spy_videos", "last_synced_at", "ALTER TABLE spy_videos ADD COLUMN last_synced_at TEXT DEFAULT ''"),
        ("spy_videos", "published_ts", "ALTER TABLE spy_videos ADD COLUMN published_ts INTEGER DEFAULT 0"),
        # Spy: channel-level sync summary
        ("spy_channels", "last_sync_new", "ALTER TABLE spy_channels ADD COLUMN last_sync_new INTEGER DEFAULT 0"),
        ("spy_channels", "total_views", "ALTER TABLE spy_channels ADD COLUMN total_views INTEGER DEFAULT 0"),
        # Studio: timeline tại thời điểm ghép, để biết bản ghép có còn khớp
        # với các thiết lập hiện tại không (đổi nhạc mà quên ghép lại)
        ("studio_projects", "base_timeline", "ALTER TABLE studio_projects ADD COLUMN base_timeline TEXT DEFAULT ''"),
    ]
    for table, column, sql in migrations:
        cursor = await db.execute(f"PRAGMA table_info({table})")
        cols = [row[1] for row in await cursor.fetchall()]
        if column not in cols:
            await db.execute(sql)
            await db.commit()

    # Fix variants table: rebuild without FK constraint if video_id is INTEGER
    await _migrate_variants_table(db)



async def _migrate_variants_table(db: aiosqlite.Connection) -> None:
    """Rebuild variants table without FK constraint if needed."""
    try:
        # Check if variants table has FK constraint (old schema)
        cursor = await db.execute("PRAGMA foreign_key_list(variants)")
        fk_list = await cursor.fetchall()
        if not fk_list:
            return  # No FK = already migrated or new DB

        import logging
        logging.getLogger(__name__).info("Migrating variants table: removing FK constraint...")

        await db.execute("PRAGMA foreign_keys=OFF")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS variants_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                profile TEXT DEFAULT 'medium',
                transforms TEXT DEFAULT '[]',
                filesize INTEGER DEFAULT 0,
                duration REAL DEFAULT 0,
                width INTEGER DEFAULT 0,
                height INTEGER DEFAULT 0,
                status TEXT DEFAULT 'ready',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            INSERT INTO variants_new (id, video_id, filename, filepath, profile, transforms, filesize, duration, width, height, status, created_at)
            SELECT id, CAST(video_id AS TEXT), filename, filepath, profile, transforms, filesize, duration, width, height, status, created_at
            FROM variants
        """)
        await db.execute("DROP TABLE variants")
        await db.execute("ALTER TABLE variants_new RENAME TO variants")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_variants_video ON variants(video_id)")
        await db.execute("PRAGMA foreign_keys=ON")
        await db.commit()
        logging.getLogger(__name__).info("Variants table migrated successfully.")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Variants migration skipped: {e}")


async def get_setting(key: str, default: str = "") -> str:
    db = await get_db()
    cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = await cursor.fetchone()
    return row["value"] if row else default


async def set_setting(key: str, value: str) -> None:
    db = await get_db()
    await db.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        (key, value),
    )
    await db.commit()


async def get_all_settings() -> dict:
    db = await get_db()
    cursor = await db.execute("SELECT key, value FROM settings")
    rows = await cursor.fetchall()
    return {row["key"]: row["value"] for row in rows}
