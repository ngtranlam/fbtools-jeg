"""Platform publisher router — dispatches publishing to the correct platform service."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


async def publish_to_platform(
    platform: str,
    target_id: int,
    filepath: str,
    caption: str,
    **kwargs,
) -> dict:
    """Route publishing to the correct platform service.

    Args:
        platform: 'facebook', 'pinterest', or 'youtube'
        target_id: page_id (facebook) or channel_id (pinterest/youtube)
        filepath: path to video file
        caption: caption / description
        **kwargs: platform-specific options

    Returns:
        dict with platform_post_id and platform-specific data
    """
    log.info(f"Publishing to {platform} (target={target_id})")

    if platform == "facebook":
        from backend.services.facebook import publish_reel
        result = await publish_reel(target_id, filepath, caption)
        return {
            "platform": "facebook",
            "platform_post_id": result.get("fb_post_id", ""),
            **result,
        }

    elif platform == "pinterest":
        from backend.services.pinterest import publish_video_pin
        board_id = kwargs.get("board_id", "")
        title = kwargs.get("title", caption[:100])
        link = kwargs.get("link", "")
        return await publish_video_pin(
            channel_id=target_id,
            filepath=filepath,
            title=title,
            description=caption,
            board_id=board_id,
            link=link,
        )

    elif platform == "youtube":
        from backend.services.youtube import upload_video
        title = kwargs.get("youtube_title", caption[:100])
        tags = kwargs.get("youtube_tags", [])
        privacy = kwargs.get("youtube_privacy", "public")
        made_for_kids = kwargs.get("made_for_kids", False)
        return await upload_video(
            channel_id=target_id,
            filepath=filepath,
            title=title,
            description=caption,
            tags=tags,
            privacy=privacy,
            made_for_kids=made_for_kids,
        )

    else:
        raise ValueError(f"Unknown platform: {platform}")
