"""Pinterest Browser Automation — Upload Video Pins via Camoufox (no API required).

Flow:
  1. Login: Open browser for manual login → save cookies
  2. Get Boards: Parse boards from Pinterest settings
  3. Create Pin: Upload video + title + description + link + board
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time
from pathlib import Path

log = logging.getLogger(__name__)

PINTEREST_URL = "https://www.pinterest.com"
COOKIES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "pinterest_sessions"
COOKIES_DIR.mkdir(parents=True, exist_ok=True)


def _cookies_path(account_name: str) -> Path:
    safe = "".join(c if c.isalnum() else "_" for c in account_name)
    return COOKIES_DIR / f"{safe}_cookies.json"


async def _human_delay(min_s: float = 0.5, max_s: float = 2.0):
    await asyncio.sleep(random.uniform(min_s, max_s))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LOGIN — Open browser for manual login
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def login_pinterest(account_name: str) -> dict:
    """Open Camoufox browser for user to manually login to Pinterest.
    
    Returns: {success, message, username}
    """
    from camoufox.async_api import AsyncCamoufox

    cookies_file = _cookies_path(account_name)
    log.info(f"Pinterest login: Opening browser for '{account_name}'")

    try:
        async with AsyncCamoufox(
            headless=False,
            humanize=True,
            i_know_what_im_doing=True,
        ) as browser:
            context = await browser.new_context()

            # Load existing cookies if available
            if cookies_file.exists():
                try:
                    cookies = json.loads(cookies_file.read_text(encoding="utf-8"))
                    await context.add_cookies(cookies)
                    log.info(f"Loaded {len(cookies)} existing cookies")
                except Exception:
                    pass

            page = await context.new_page()
            await page.goto(f"{PINTEREST_URL}/login/", wait_until="domcontentloaded")
            await _human_delay(1, 2)

            # Check if already logged in
            if "/login" not in page.url:
                log.info("Already logged in via cookies")
            else:
                # Wait for user to complete login manually (max 5 minutes)
                log.info("Waiting for user to login manually...")
                try:
                    await page.wait_for_url(
                        lambda url: "/login" not in url and "pinterest.com" in url,
                        timeout=300_000,  # 5 minutes
                    )
                except Exception:
                    return {"success": False, "message": "Login timeout — hết 5 phút chưa đăng nhập"}

            await _human_delay(2, 3)

            # Verify login by checking for user menu
            username = ""
            try:
                # Navigate to settings to get username
                await page.goto(f"{PINTEREST_URL}/settings/", wait_until="domcontentloaded")
                await _human_delay(2, 3)

                # Try to extract username from page
                username_el = await page.query_selector('[data-test-id="header-profile"] img, [data-test-id="user-menu"] img')
                if username_el:
                    username = await username_el.get_attribute("alt") or ""

                # Alternative: get from URL redirect
                if not username:
                    current_url = page.url
                    if "pinterest.com/" in current_url:
                        parts = current_url.rstrip("/").split("/")
                        if len(parts) > 3:
                            username = parts[-1] if parts[-1] != "settings" else ""
            except Exception as e:
                log.warning(f"Could not extract username: {e}")

            # Save cookies for future sessions
            cookies = await context.cookies()
            cookies_file.write_text(json.dumps(cookies, ensure_ascii=False), encoding="utf-8")
            log.info(f"Saved {len(cookies)} cookies for '{account_name}'")

            return {
                "success": True,
                "message": f"Đăng nhập Pinterest thành công!",
                "username": username or account_name,
                "cookies_count": len(cookies),
            }

    except Exception as e:
        log.error(f"Pinterest login error: {e}")
        return {"success": False, "message": f"Lỗi: {str(e)}"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  GET BOARDS — Parse from Pinterest UI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def get_boards_browser(account_name: str) -> list[dict]:
    """Get list of boards for a Pinterest account using browser cookies."""
    from camoufox.async_api import AsyncCamoufox

    cookies_file = _cookies_path(account_name)
    if not cookies_file.exists():
        raise ValueError(f"Chưa đăng nhập Pinterest cho '{account_name}'. Vui lòng đăng nhập trước.")

    cookies = json.loads(cookies_file.read_text(encoding="utf-8"))
    boards = []

    try:
        async with AsyncCamoufox(
            headless=True,
            humanize=False,
            i_know_what_im_doing=True,
        ) as browser:
            context = await browser.new_context()
            await context.add_cookies(cookies)
            page = await context.new_page()

            # Use Pinterest's internal API via cookie-authenticated request
            # Navigate to pin creation page which loads boards
            await page.goto(
                f"{PINTEREST_URL}/pin-creation-tool/",
                wait_until="domcontentloaded",
            )
            await _human_delay(2, 4)

            # Method 1: Extract boards from the board selector dropdown
            # Click on board selector to open dropdown
            board_selector = await page.query_selector(
                '[data-test-id="board-dropdown-select-button"], '
                '[data-test-id="boardDropdownSelectButton"], '
                'button[aria-label*="Board"], '
                'button[aria-label*="board"], '
                '[data-test-id="create-board-picker"]'
            )

            if board_selector:
                await board_selector.click()
                await _human_delay(1, 2)

                # Get board items
                board_items = await page.query_selector_all(
                    '[data-test-id="board-row"], '
                    '[data-test-id="boardRow"], '
                    'div[role="option"], '
                    'li[role="option"], '
                    '[data-test-id="board-dropdown-item"]'
                )

                for item in board_items:
                    try:
                        name = (await item.inner_text()).strip()
                        if name and name not in ("Create board", "Tạo board", ""):
                            board_id = await item.get_attribute("data-test-id") or ""
                            boards.append({
                                "id": board_id or name,
                                "name": name,
                                "type": "board",
                            })
                    except Exception:
                        continue

            # Method 2: Fallback — parse boards from profile page
            if not boards:
                log.info("Fallback: Parsing boards from profile page")
                await page.goto(PINTEREST_URL, wait_until="domcontentloaded")
                await _human_delay(2, 3)

                # Find profile link and navigate
                profile_link = await page.query_selector(
                    '[data-test-id="header-profile"] a, '
                    'a[href*="/settings"]'
                )
                if profile_link:
                    href = await profile_link.get_attribute("href")
                    if href:
                        username = href.strip("/").split("/")[-1]
                        await page.goto(
                            f"{PINTEREST_URL}/{username}/_saved/",
                            wait_until="domcontentloaded"
                        )
                        await _human_delay(2, 3)

                        # Parse board cards
                        board_links = await page.query_selector_all(
                            'a[href*="/' + username + '/"]'
                        )
                        seen = set()
                        for link in board_links:
                            try:
                                href = await link.get_attribute("href") or ""
                                text = (await link.inner_text()).strip()
                                # Filter: board links look like /username/boardname/
                                parts = href.strip("/").split("/")
                                if len(parts) >= 2 and text and text not in seen:
                                    board_name = parts[-1] if parts[-1] != "_saved" else ""
                                    if board_name and board_name != username:
                                        seen.add(text)
                                        boards.append({
                                            "id": board_name,
                                            "name": text.split("\n")[0],
                                            "type": "board",
                                        })
                            except Exception:
                                continue

            # Method 3: Use Pinterest's internal resource API
            if not boards:
                log.info("Fallback 2: Using Pinterest resource API")
                try:
                    resp = await page.evaluate("""
                        async () => {
                            try {
                                const resp = await fetch('/resource/BoardsResource/get/', {
                                    method: 'POST',
                                    headers: {'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'},
                                    body: JSON.stringify({
                                        options: {
                                            privacy_filter: "all",
                                            sort: "custom",
                                            field_set_key: "detailed",
                                            page_size: 50
                                        }
                                    })
                                });
                                const data = await resp.json();
                                return data?.resource_response?.data || [];
                            } catch(e) { return []; }
                        }
                    """)
                    for b in resp:
                        if isinstance(b, dict):
                            boards.append({
                                "id": b.get("id", ""),
                                "name": b.get("name", ""),
                                "pin_count": b.get("pin_count", 0),
                                "type": "board",
                            })
                except Exception as e:
                    log.warning(f"Resource API fallback failed: {e}")

            # Update cookies after session
            new_cookies = await context.cookies()
            cookies_file.write_text(json.dumps(new_cookies, ensure_ascii=False), encoding="utf-8")

    except Exception as e:
        log.error(f"Get boards error: {e}")
        raise

    log.info(f"Found {len(boards)} boards for '{account_name}'")
    return boards


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PUBLISH VIDEO PIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def publish_video_pin_browser(
    account_name: str,
    filepath: str,
    title: str,
    description: str = "",
    board_name: str = "",
    link: str = "",
) -> dict:
    """Upload a video pin via browser automation.
    
    Args:
        account_name: Pinterest account identifier
        filepath: Path to video file
        title: Pin title
        description: Pin description  
        board_name: Board name to pin to
        link: Destination URL (store/product link)
    
    Returns: {success, message, pin_url}
    """
    from camoufox.async_api import AsyncCamoufox

    cookies_file = _cookies_path(account_name)
    if not cookies_file.exists():
        return {"success": False, "message": "Chưa đăng nhập Pinterest"}

    video_path = Path(filepath)
    if not video_path.exists():
        return {"success": False, "message": f"File video không tồn tại: {filepath}"}

    cookies = json.loads(cookies_file.read_text(encoding="utf-8"))
    log.info(f"Pinterest publish: {title} → board '{board_name}' | link: {link}")

    try:
        async with AsyncCamoufox(
            headless=False,
            humanize=True,
            i_know_what_im_doing=True,
        ) as browser:
            context = await browser.new_context()
            await context.add_cookies(cookies)
            page = await context.new_page()

            # Step 1: Navigate to pin creation tool
            await page.goto(
                f"{PINTEREST_URL}/pin-creation-tool/",
                wait_until="domcontentloaded",
            )
            await _human_delay(2, 4)

            # Check if logged in
            if "/login" in page.url:
                return {"success": False, "message": "Session hết hạn, cần đăng nhập lại"}

            # Step 2: Upload video file
            log.info("Uploading video file...")
            file_input = await page.query_selector('input[type="file"]')
            if not file_input:
                # Look for drop zone and find hidden input
                file_input = await page.query_selector(
                    'input[accept*="video"], input[accept*="image"]'
                )
            
            if file_input:
                await file_input.set_input_files(str(video_path.resolve()))
            else:
                return {"success": False, "message": "Không tìm thấy nút upload trên trang"}

            # Wait for upload to complete
            log.info("Waiting for video upload...")
            await _human_delay(3, 5)

            # Wait for upload progress to finish (look for preview/thumbnail)
            try:
                await page.wait_for_selector(
                    'video, [data-test-id="pin-draft-video-player"], '
                    '[data-test-id="videoPlayer"], img[src*="pinimg"]',
                    timeout=120_000,
                )
                log.info("Video uploaded successfully")
            except Exception:
                log.warning("Video upload may still be processing, continuing...")

            await _human_delay(1, 2)

            # Step 3: Fill in title
            log.info(f"Filling title: {title[:50]}...")
            title_input = await page.query_selector(
                '[data-test-id="pin-draft-title"] [contenteditable], '
                '[data-test-id="pin-draft-title"] textarea, '
                'textarea[placeholder*="title" i], '
                'textarea[placeholder*="tiêu đề" i], '
                '[data-test-id="pin-draft-title"] input, '
                'div[data-test-id="pin-title"] [contenteditable]'
            )
            if title_input:
                await title_input.click()
                await _human_delay(0.3, 0.5)
                await page.keyboard.press("Control+a")
                await page.keyboard.type(title[:100], delay=random.randint(30, 80))
            else:
                log.warning("Could not find title input")

            await _human_delay(0.5, 1)

            # Step 4: Fill in description
            if description:
                log.info("Filling description...")
                desc_input = await page.query_selector(
                    '[data-test-id="pin-draft-description"] [contenteditable], '
                    '[data-test-id="pin-draft-description"] textarea, '
                    'textarea[placeholder*="description" i], '
                    'textarea[placeholder*="mô tả" i], '
                    'div[data-test-id="pin-description"] [contenteditable]'
                )
                if desc_input:
                    await desc_input.click()
                    await _human_delay(0.3, 0.5)
                    await page.keyboard.type(description[:500], delay=random.randint(20, 60))

            await _human_delay(0.5, 1)

            # Step 5: Fill in destination link (STORE/PRODUCT URL)
            if link:
                log.info(f"Adding destination link: {link}")
                link_input = await page.query_selector(
                    '[data-test-id="pin-draft-link"] input, '
                    'input[placeholder*="link" i], '
                    'input[placeholder*="URL" i], '
                    'input[placeholder*="website" i], '
                    'input[placeholder*="liên kết" i], '
                    'input[placeholder*="destination" i], '
                    '[data-test-id="pin-destination-link"] input'
                )
                if link_input:
                    await link_input.click()
                    await _human_delay(0.3, 0.5)
                    await page.keyboard.press("Control+a")
                    await page.keyboard.type(link, delay=random.randint(20, 50))
                else:
                    log.warning("Could not find link input field")

            await _human_delay(0.5, 1)

            # Step 6: Select board
            if board_name:
                log.info(f"Selecting board: {board_name}")
                board_btn = await page.query_selector(
                    '[data-test-id="board-dropdown-select-button"], '
                    '[data-test-id="boardDropdownSelectButton"], '
                    'button[aria-label*="Board"], '
                    'button[aria-label*="board"]'
                )
                if board_btn:
                    await board_btn.click()
                    await _human_delay(1, 2)

                    # Search for board
                    search_input = await page.query_selector(
                        'input[placeholder*="Search" i], '
                        'input[placeholder*="Tìm" i], '
                        '[data-test-id="board-search-input"] input'
                    )
                    if search_input:
                        await search_input.click()
                        await page.keyboard.type(board_name, delay=random.randint(50, 100))
                        await _human_delay(1, 2)

                    # Click matching board
                    board_found = False
                    board_options = await page.query_selector_all(
                        '[data-test-id="board-row"], '
                        'div[role="option"], '
                        'li[role="option"]'
                    )
                    for option in board_options:
                        text = (await option.inner_text()).strip()
                        if board_name.lower() in text.lower():
                            await option.click()
                            board_found = True
                            log.info(f"Selected board: {text}")
                            break

                    if not board_found:
                        log.warning(f"Board '{board_name}' not found, using default")

            await _human_delay(1, 2)

            # Step 7: Click Publish
            log.info("Publishing pin...")
            publish_btn = await page.query_selector(
                '[data-test-id="board-dropdown-save-button"], '
                'button[data-test-id="create-new-pin"], '
                'button:has-text("Publish"), '
                'button:has-text("Xuất bản"), '
                'button:has-text("Save"), '
                'button:has-text("Lưu")'
            )

            if not publish_btn:
                # Try broader selector
                buttons = await page.query_selector_all('button')
                for btn in buttons:
                    text = (await btn.inner_text()).strip().lower()
                    if text in ("publish", "save", "xuất bản", "lưu", "đăng"):
                        publish_btn = btn
                        break

            if publish_btn:
                await publish_btn.click()
                await _human_delay(3, 5)
                log.info("Pin published!")
            else:
                return {"success": False, "message": "Không tìm thấy nút Publish"}

            # Step 8: Verify and get pin URL
            await _human_delay(2, 3)
            current_url = page.url
            pin_url = current_url if "/pin/" in current_url else ""

            # Save updated cookies
            new_cookies = await context.cookies()
            cookies_file.write_text(json.dumps(new_cookies, ensure_ascii=False), encoding="utf-8")

            return {
                "success": True,
                "message": f"✅ Đã đăng Video Pin lên board '{board_name}'!",
                "pin_url": pin_url,
                "board": board_name,
                "link": link,
            }

    except Exception as e:
        log.error(f"Pinterest publish error: {e}")
        return {"success": False, "message": f"Lỗi: {str(e)}"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  VALIDATE — Check if cookies are still valid
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def validate_session(account_name: str) -> dict:
    """Check if Pinterest session is still valid."""
    from camoufox.async_api import AsyncCamoufox

    cookies_file = _cookies_path(account_name)
    if not cookies_file.exists():
        return {"valid": False, "error": "Chưa đăng nhập"}

    cookies = json.loads(cookies_file.read_text(encoding="utf-8"))

    try:
        async with AsyncCamoufox(
            headless=True,
            humanize=False,
            i_know_what_im_doing=True,
        ) as browser:
            context = await browser.new_context()
            await context.add_cookies(cookies)
            page = await context.new_page()

            await page.goto(
                f"{PINTEREST_URL}/settings/",
                wait_until="domcontentloaded",
            )
            await _human_delay(2, 3)

            if "/login" in page.url:
                return {"valid": False, "error": "Session hết hạn, cần đăng nhập lại"}

            # Try to get username
            username = ""
            try:
                title = await page.title()
                if title:
                    username = title.replace("Pinterest", "").replace("Settings", "").replace("·", "").strip()
            except Exception:
                pass

            return {"valid": True, "username": username or account_name}

    except Exception as e:
        return {"valid": False, "error": str(e)}


async def delete_session(account_name: str) -> bool:
    """Delete saved cookies for an account."""
    cookies_file = _cookies_path(account_name)
    if cookies_file.exists():
        cookies_file.unlink()
        return True
    return False
