"""YouTube Data API v3 service — Upload videos via resumable upload."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import httpx

from backend.database import get_db

log = logging.getLogger(__name__)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
YOUTUBE_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Chunk size for resumable upload (5MB)
UPLOAD_CHUNK_SIZE = 5 * 1024 * 1024


async def _get_channel_credentials(channel_id: int) -> dict:
    """Load credentials from channels table."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT credentials, extra_data FROM channels WHERE id = ? AND platform = 'youtube'",
        (channel_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise ValueError(f"YouTube channel {channel_id} not found")

    creds = json.loads(row["credentials"]) if row["credentials"] else {}
    extra = json.loads(row["extra_data"]) if row["extra_data"] else {}
    return {**creds, **extra}


async def _refresh_access_token(channel_id: int) -> str:
    """Refresh OAuth2 access token using refresh_token."""
    creds = await _get_channel_credentials(channel_id)
    refresh_token = creds.get("refresh_token", "")
    client_id = creds.get("client_id", "") or os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = creds.get("client_secret", "") or os.getenv("GOOGLE_CLIENT_SECRET", "")

    if not refresh_token:
        raise ValueError("YouTube refresh token not configured")
    if not client_id or not client_secret:
        raise ValueError("Google OAuth client_id/secret not configured")

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        new_token = data.get("access_token", "")

        if new_token:
            # Update stored credentials
            db = await get_db()
            cursor = await db.execute(
                "SELECT credentials FROM channels WHERE id = ?", (channel_id,)
            )
            row = await cursor.fetchone()
            stored_creds = json.loads(row["credentials"]) if row and row["credentials"] else {}
            stored_creds["access_token"] = new_token
            await db.execute(
                "UPDATE channels SET credentials = ?, updated_at = datetime('now') WHERE id = ?",
                (json.dumps(stored_creds), channel_id),
            )
            await db.commit()
            log.info(f"YouTube: Refreshed access token for channel {channel_id}")

        return new_token


async def _get_valid_token(channel_id: int) -> str:
    """Get a valid access token, refreshing if needed."""
    creds = await _get_channel_credentials(channel_id)
    access_token = creds.get("access_token", "")

    if not access_token:
        return await _refresh_access_token(channel_id)

    # Test token validity
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{YOUTUBE_API_BASE}/channels",
            params={"part": "id", "mine": "true"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code == 401:
            return await _refresh_access_token(channel_id)

    return access_token


async def upload_video(
    channel_id: int,
    filepath: str,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    privacy: str = "public",
    made_for_kids: bool = False,
    category_id: str = "22",  # 22 = People & Blogs
) -> dict:
    """Upload a video to YouTube using resumable upload.

    Args:
        channel_id: Internal channel ID
        filepath: Path to video file
        title: Video title (max 100 chars)
        description: Video description (max 5000 chars)
        tags: List of tags
        privacy: public, unlisted, or private
        made_for_kids: COPPA compliance flag
        category_id: YouTube category ID
    """
    access_token = await _get_valid_token(channel_id)
    file_path = Path(filepath)
    if not file_path.exists():
        raise FileNotFoundError(f"Video file not found: {filepath}")

    file_size = file_path.stat().st_size
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Length": str(file_size),
        "X-Upload-Content-Type": "video/mp4",
    }

    # Video metadata
    video_metadata = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": (tags or [])[:30],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }

    async with httpx.AsyncClient(timeout=300) as client:
        # Step 1: Initialize resumable upload
        log.info(f"YouTube: Initializing upload for {file_path.name} ({file_size} bytes)")
        init_resp = await client.post(
            YOUTUBE_UPLOAD_URL,
            params={
                "uploadType": "resumable",
                "part": "snippet,status",
            },
            headers=headers,
            json=video_metadata,
        )
        init_resp.raise_for_status()

        upload_url = init_resp.headers.get("Location", "")
        if not upload_url:
            raise ValueError("YouTube did not return resumable upload URL")

        # Step 2: Upload video in chunks
        log.info(f"YouTube: Uploading video to {upload_url[:80]}...")
        with open(file_path, "rb") as f:
            video_data = f.read()

        upload_resp = await client.put(
            upload_url,
            content=video_data,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "video/mp4",
                "Content-Length": str(file_size),
            },
            timeout=600,  # 10min timeout for large files
        )
        upload_resp.raise_for_status()
        result = upload_resp.json()

        video_id = result.get("id", "")
        log.info(f"YouTube: Video uploaded successfully — ID: {video_id}")

        return {
            "platform": "youtube",
            "platform_post_id": video_id,
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
            "title": result.get("snippet", {}).get("title", ""),
            "privacy": result.get("status", {}).get("privacyStatus", ""),
        }


async def get_channel_info(channel_id: int) -> dict:
    """Get YouTube channel info."""
    access_token = await _get_valid_token(channel_id)

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{YOUTUBE_API_BASE}/channels",
            params={"part": "snippet,statistics", "mine": "true"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        if not items:
            return {"error": "No channel found"}

        ch = items[0]
        return {
            "channel_id": ch.get("id", ""),
            "title": ch.get("snippet", {}).get("title", ""),
            "description": ch.get("snippet", {}).get("description", ""),
            "thumbnail": ch.get("snippet", {}).get("thumbnails", {}).get("default", {}).get("url", ""),
            "subscribers": ch.get("statistics", {}).get("subscriberCount", "0"),
            "video_count": ch.get("statistics", {}).get("videoCount", "0"),
            "view_count": ch.get("statistics", {}).get("viewCount", "0"),
        }


async def validate_credentials(channel_id: int) -> dict:
    """Test if YouTube credentials are valid."""
    try:
        info = await get_channel_info(channel_id)
        if "error" in info:
            return {"valid": False, "error": info["error"]}
        return {
            "valid": True,
            "channel_title": info.get("title", ""),
            "subscribers": info.get("subscribers", "0"),
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}
