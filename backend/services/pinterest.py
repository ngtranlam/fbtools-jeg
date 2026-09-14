"""Pinterest API service — Upload video pins."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import httpx

from backend.database import get_db

log = logging.getLogger(__name__)

PINTEREST_API_BASE = "https://api.pinterest.com/v5"


async def _get_channel_credentials(channel_id: int) -> dict:
    """Load credentials from channels table."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT credentials, extra_data FROM channels WHERE id = ? AND platform = 'pinterest'",
        (channel_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise ValueError(f"Pinterest channel {channel_id} not found")

    creds = json.loads(row["credentials"]) if row["credentials"] else {}
    extra = json.loads(row["extra_data"]) if row["extra_data"] else {}
    return {**creds, **extra}


async def get_boards(channel_id: int) -> list[dict]:
    """List all boards for a Pinterest account."""
    creds = await _get_channel_credentials(channel_id)
    access_token = creds.get("access_token", "")
    if not access_token:
        raise ValueError("Pinterest access token not configured")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{PINTEREST_API_BASE}/boards",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"page_size": 50},
        )
        resp.raise_for_status()
        data = resp.json()
        boards = []
        for b in data.get("items", []):
            boards.append({
                "id": b.get("id", ""),
                "name": b.get("name", ""),
                "description": b.get("description", ""),
                "pin_count": b.get("pin_count", 0),
                "privacy": b.get("privacy", "PUBLIC"),
            })
        return boards


async def publish_video_pin(
    channel_id: int,
    filepath: str,
    title: str,
    description: str = "",
    board_id: str = "",
    link: str = "",
) -> dict:
    """Upload a video as a Pin to Pinterest.
    
    Pinterest video pin flow:
    1. Register media upload
    2. Upload video file
    3. Create pin with media_id
    """
    creds = await _get_channel_credentials(channel_id)
    access_token = creds.get("access_token", "")
    if not access_token:
        raise ValueError("Pinterest access token not configured")
    if not board_id:
        raise ValueError("Board ID is required for Pinterest publishing")

    file_path = Path(filepath)
    if not file_path.exists():
        raise FileNotFoundError(f"Video file not found: {filepath}")

    file_size = file_path.stat().st_size
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=120) as client:
        # Step 1: Register media upload
        log.info(f"Pinterest: Registering media upload for {file_path.name}")
        register_resp = await client.post(
            f"{PINTEREST_API_BASE}/media",
            headers={**headers, "Content-Type": "application/json"},
            json={"media_type": "video"},
        )
        register_resp.raise_for_status()
        register_data = register_resp.json()
        media_id = register_data.get("media_id", "")
        upload_url = register_data.get("upload_url", "")
        upload_params = register_data.get("upload_parameters", {})

        if not upload_url:
            raise ValueError("Pinterest did not return upload URL")

        # Step 2: Upload video file (multipart)
        log.info(f"Pinterest: Uploading video ({file_size} bytes) to {upload_url}")
        with open(file_path, "rb") as f:
            files_data = {**upload_params, "file": (file_path.name, f, "video/mp4")}
            # Pinterest uses a separate upload endpoint
            upload_resp = await client.post(
                upload_url,
                data={k: v for k, v in upload_params.items()},
                files={"file": (file_path.name, f, "video/mp4")},
                timeout=300,
            )

        log.info(f"Pinterest: Upload response status {upload_resp.status_code}")

        # Step 3: Create pin with media
        log.info(f"Pinterest: Creating pin on board {board_id}")
        pin_data = {
            "title": title[:100],  # Pinterest max 100 chars
            "description": description[:500],
            "board_id": board_id,
            "media_source": {
                "source_type": "video_id",
                "media_id": media_id,
            },
        }
        if link:
            pin_data["link"] = link

        create_resp = await client.post(
            f"{PINTEREST_API_BASE}/pins",
            headers={**headers, "Content-Type": "application/json"},
            json=pin_data,
        )
        create_resp.raise_for_status()
        pin_result = create_resp.json()

        pin_id = pin_result.get("id", "")
        log.info(f"Pinterest: Pin created successfully — ID: {pin_id}")

        return {
            "platform": "pinterest",
            "platform_post_id": pin_id,
            "pin_url": f"https://www.pinterest.com/pin/{pin_id}/",
            "media_id": media_id,
            "board_id": board_id,
        }


async def validate_credentials(channel_id: int) -> dict:
    """Test if Pinterest credentials are valid."""
    try:
        creds = await _get_channel_credentials(channel_id)
        access_token = creds.get("access_token", "")
        if not access_token:
            return {"valid": False, "error": "No access token"}

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{PINTEREST_API_BASE}/user_account",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "valid": True,
                    "username": data.get("username", ""),
                    "account_type": data.get("account_type", ""),
                }
            else:
                return {"valid": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"valid": False, "error": str(e)}
