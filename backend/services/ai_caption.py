"""AI Caption Rewrite — GPT-4o-mini powered viral caption generator."""

from __future__ import annotations

import logging
import httpx

from backend.database import get_setting

log = logging.getLogger(__name__)

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are a viral social media copywriter specialized in Reels, Shorts, and TikTok short videos for US/UK/Canada audiences.

## ABSOLUTE RULES
1. NO emoji — completely banned, no exceptions.
2. SHORT captions — same length or shorter than the original. Max 2-3 lines.
3. Write naturally, conversationally — like a real person talking, not corporate marketing.
4. First line is the HOOK — trigger curiosity (question, bold claim, or call out the audience).
5. NO generic CTAs ("like share comment") — if CTA is needed, make it natural and subtle.

## CAPTION STYLE
- Tone: punchy, direct, slightly mysterious or controversial
- Reels/TikTok style: 1-2 hook sentences + 1 supporting line if needed
- Use "..." to create curiosity gaps
- Use CAPS on 1-2 words for emphasis
- Write in American English, casual and relatable for Gen Z / Millennials
- Reference trending culture, slang, or relatable moments when fitting

## HASHTAGS
- 5-8 relevant hashtags
- Mix: 2 large trending tags + 3-4 niche tags + 1-2 brand/page tags
- No spaces inside hashtags, separated by spaces

## OUTPUT FORMAT (return EXACTLY this format, no explanations)

[CAPTION]
{short caption, no emoji}

[HASHTAGS]
{hashtags separated by spaces}
"""


async def rewrite_caption(
    original_caption: str,
    page_name: str,
    page_category: str = "",
    video_title: str = "",
    language: str = "en",
) -> dict:
    """Rewrite a caption using GPT-4o-mini for viral optimization."""
    api_key = await get_setting("openai_api_key", "")
    if not api_key:
        return {"error": "OpenAI API Key not configured. Go to Settings to add it."}

    # Build context from video title + caption
    video_context = ""
    if video_title:
        video_context = f"\n- Original video title: {video_title}"

    user_prompt = f"""## INFO
- Page name: {page_name}
- Category: {page_category or 'General'}
- Target audience: US, UK, Canada (English-speaking){video_context}

## ORIGINAL CAPTION
{original_caption or '(No original caption — create one based on the page name and video title)'}

## TASK
Rewrite as a viral caption + hashtags for the page "{page_name}".{' Combine the video title and original caption to create the strongest possible hook.' if video_title else ''} Write in natural American English."""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                OPENAI_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.8,
                    "max_tokens": 500,
                },
            )

        if r.status_code != 200:
            error_data = r.json()
            error_msg = error_data.get("error", {}).get("message", f"HTTP {r.status_code}")
            log.error(f"OpenAI API error: {error_msg}")
            return {"error": f"OpenAI error: {error_msg}"}

        data = r.json()
        content = data["choices"][0]["message"]["content"].strip()

        # Parse response
        caption = content
        hashtags = ""

        if "[CAPTION]" in content:
            parts = content.split("[HASHTAGS]")
            caption = parts[0].replace("[CAPTION]", "").strip()
            if len(parts) > 1:
                hashtags = parts[1].strip()

        # Calculate token usage for cost tracking
        usage = data.get("usage", {})
        tokens_used = usage.get("total_tokens", 0)

        log.info(f"AI caption generated for '{page_name}': {tokens_used} tokens used")

        return {
            "caption": caption,
            "hashtags": hashtags,
            "full_text": f"{caption}\n\n{hashtags}".strip(),
            "tokens_used": tokens_used,
            "model": MODEL,
        }

    except httpx.TimeoutException:
        return {"error": "OpenAI timeout — please try again."}
    except Exception as e:
        log.error(f"AI caption error: {e}")
        return {"error": f"Error: {str(e)}"}


async def rewrite_caption_batch(
    original_caption: str,
    pages: list[dict],
    language: str = "en",
) -> list[dict]:
    """Rewrite caption for multiple pages (each gets unique hashtags)."""
    results = []
    for page in pages:
        result = await rewrite_caption(
            original_caption=original_caption,
            page_name=page.get("page_name", ""),
            page_category=page.get("category", ""),
            language=language,
        )
        result["page_id"] = page.get("id")
        result["page_name"] = page.get("page_name", "")
        results.append(result)
    return results


SPIN_PROMPT = """You are a viral social media copywriter for US/UK/Canada audiences.

## TASK
Create {count} COMPLETELY DIFFERENT caption versions for the same video, each for a different Facebook Page.
Each caption must:
1. Use DIFFERENT wording, angle, and hook — NEVER repeat the same opening
2. NO emoji — strictly forbidden
3. Short 1-3 lines, Reels/TikTok style
4. Include 5-8 unique hashtags per version
5. Write in natural American English, casual and authentic
6. Vary the tone: some edgy, some curious, some relatable, some bold

## OUTPUT FORMAT (JSON array, no explanations)
[
  {{"page_id": 1, "caption": "...", "hashtags": "#tag1 #tag2"}},
  {{"page_id": 2, "caption": "...", "hashtags": "#tag1 #tag2"}}
]
"""


async def spin_captions(
    base_caption: str,
    page_ids: list[int],
    video_title: str = "",
    language: str = "en",
) -> dict:
    """Generate N unique caption spins in a single GPT call."""
    import json as json_mod

    api_key = await get_setting("openai_api_key", "")
    if not api_key:
        return {"error": "OpenAI API Key not configured."}

    count = len(page_ids)
    if count == 0:
        return {"error": "No pages selected."}

    video_context = f"\n- Video title: {video_title}" if video_title else ""

    user_prompt = f"""## INFO
- Number of captions to create: {count}
- Page IDs: {page_ids}
- Target audience: US, UK, Canada (English-speaking){video_context}

## ORIGINAL CAPTION
{base_caption or '(Create from scratch based on the video title)'}

## TASK
Create {count} completely different captions. Each one must use a different hook, angle, and style. Write in natural American English."""

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            r = await client.post(
                OPENAI_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": SPIN_PROMPT.format(count=count)},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.9,
                    "max_tokens": 300 * count,
                    "response_format": {"type": "json_object"},
                },
            )

        if r.status_code != 200:
            error_data = r.json()
            return {"error": f"OpenAI error: {error_data.get('error', {}).get('message', r.status_code)}"}

        data = r.json()
        content = data["choices"][0]["message"]["content"].strip()
        usage = data.get("usage", {})
        tokens_used = usage.get("total_tokens", 0)

        # Parse JSON response
        try:
            parsed = json_mod.loads(content)
            # Handle both {"spins": [...]} and direct array
            spins = parsed if isinstance(parsed, list) else parsed.get("spins", parsed.get("captions", []))
            if isinstance(spins, dict):
                spins = list(spins.values()) if spins else []
        except json_mod.JSONDecodeError:
            return {"error": "AI response not valid JSON format"}

        # Map page_ids to spins
        result_map = {}
        for i, pid in enumerate(page_ids):
            if i < len(spins):
                spin = spins[i]
                caption = spin.get("caption", "")
                hashtags = spin.get("hashtags", "")
                result_map[pid] = f"{caption}\n\n{hashtags}".strip()
            else:
                result_map[pid] = base_caption  # fallback

        log.info(f"Spin captions generated: {count} versions, {tokens_used} tokens")
        return {
            "spins": result_map,
            "tokens_used": tokens_used,
            "model": MODEL,
        }

    except httpx.TimeoutException:
        return {"error": "OpenAI timeout — please try again."}
    except Exception as e:
        log.error(f"Spin caption error: {e}")
        return {"error": f"Error: {str(e)}"}

