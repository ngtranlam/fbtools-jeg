"""Auto-comment service with 30 English dropshipping comment templates for US/UK/Canada markets."""

from __future__ import annotations

import asyncio
import json
import logging
import random
from datetime import datetime

from backend.database import get_db, get_setting
from backend.services.facebook import post_comment

log = logging.getLogger(__name__)

# ── 30 Comment Templates (English, optimized for US/UK/Canada) ────

COMMENT_TEMPLATES = [
    # Urgency / Scarcity
    "This is selling out FAST. Grab yours at {store_url} before it's gone",
    "Only a few left in stock... don't sleep on this. {store_url}",
    "Limited time deal, won't last. Check it out at {store_url}",
    "This deal ends tonight. Get yours now at {store_url}",
    "Best seller alert... almost sold out. {store_url}",

    # Social Proof
    "Just got mine and honestly it's even better in person. {store_url}",
    "Ordered last week, already obsessed. Highly recommend. {store_url}",
    "Over 10K happy customers can't be wrong. See why at {store_url}",
    "My whole friend group has one now lol. Get yours at {store_url}",
    "The reviews speak for themselves. Check them out at {store_url}",

    # Curiosity
    "Wait... you saw the product in the video right? It's at {store_url}",
    "Everyone keeps asking where to get this. Here you go: {store_url}",
    "This went viral for a reason. Find out why at {store_url}",
    "The product from the video is right here: {store_url}",
    "If you're wondering where to buy this... {store_url}. You're welcome",

    # Benefit-focused
    "Free shipping + hassle-free returns. What's not to love? {store_url}",
    "Premium quality at an unbeatable price. Shop at {store_url}",
    "30-day money back guarantee. Zero risk. {store_url}",
    "Ships fast from the US. Free shipping nationwide. {store_url}",
    "Quality you can feel the moment you open the box. {store_url}",

    # Call to Action
    "Shop now at {store_url} -- new customers get a special discount",
    "Click the link to order today: {store_url}",
    "Ready to upgrade? Start here: {store_url}",
    "Browse the full collection and order at {store_url}",
    "Link to the official store: {store_url}",

    # Question / Conversational
    "Anyone else need this in their life? {store_url}",
    "Who else is adding this to cart right now? {store_url}",
    "Need one? Easy ordering at {store_url} -- fast shipping too",
    "Is it just me or is this the coolest thing ever? {store_url}",
    "SALE is live right now. Don't miss it. {store_url}",
]


async def execute_auto_comment(post_id: int) -> dict:
    """Auto-comment on a viral post with store link."""
    enabled = await get_setting("auto_comment_enabled", "false")
    if enabled != "true":
        return {"success": False, "reason": "auto_comment disabled"}

    db = await get_db()
    try:
        # Check if already commented
        cursor = await db.execute(
            "SELECT comment_sent FROM viral_alerts WHERE post_id = ? AND comment_sent = 1 LIMIT 1",
            (post_id,),
        )
        if await cursor.fetchone():
            return {"success": False, "reason": "already commented"}

        # Get post + page info
        cursor = await db.execute(
            """SELECT p.id, p.fb_post_id, p.page_id,
                      pg.store_url, pg.comment_templates, pg.page_name
               FROM posts p JOIN pages pg ON p.page_id = pg.id
               WHERE p.id = ?""",
            (post_id,),
        )
        post = await cursor.fetchone()
        if not post:
            return {"success": False, "reason": "post not found"}

        store_url = post["store_url"]
        if not store_url:
            return {"success": False, "reason": "no store_url configured for page"}

        fb_post_id = post["fb_post_id"]
        if not fb_post_id:
            return {"success": False, "reason": "no fb_post_id"}

        # Pick template
        custom_templates = json.loads(post["comment_templates"] or "[]")
        templates = custom_templates if custom_templates else COMMENT_TEMPLATES
        template = random.choice(templates)
        message = template.replace("{store_url}", store_url)

        # Image attachment (if page has store_image_url configured)
        attachment_url = post["store_image_url"] if "store_image_url" in post.keys() else ""

        # Random delay for safety
        delay_min = int(await get_setting("auto_comment_delay_min", "30"))
        delay_max = int(await get_setting("auto_comment_delay_max", "120"))
        delay = random.randint(delay_min, delay_max)
        log.info(f"Auto-comment delay: {delay}s for post {post_id}")
        await asyncio.sleep(delay)

        # Post comment (with optional image)
        result = await post_comment(post["page_id"], fb_post_id, message, attachment_url=attachment_url or "")

        # Mark as commented
        await db.execute(
            "UPDATE viral_alerts SET comment_sent = 1 WHERE post_id = ?",
            (post_id,),
        )
        await db.commit()

        return {
            "success": True,
            "comment_id": result.get("id", ""),
            "message": message,
            "page_name": post["page_name"],
        }

    except Exception as e:
        log.error(f"Auto-comment failed for post {post_id}: {e}")
        return {"success": False, "reason": str(e)}
