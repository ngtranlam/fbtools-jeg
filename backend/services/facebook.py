"""Facebook Graph API service — accounts, pages, reels, insights, comments."""

from __future__ import annotations

import json
import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

from backend.database import get_db
from backend.utils.crypto import encrypt_token, decrypt_token

log = logging.getLogger(__name__)
GRAPH_URL = "https://graph.facebook.com/v25.0"
TIMEOUT = httpx.Timeout(60.0, connect=10.0)


# ── Account Management ───────────────────────────────────────

async def validate_token(access_token: str) -> dict:
    """Validate a user access token and return user info."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(f"{GRAPH_URL}/me", params={
            "access_token": access_token,
            "fields": "id,name,email",
        })
        r.raise_for_status()
        return r.json()


async def get_long_lived_token(access_token: str, app_id: str, app_secret: str) -> dict:
    """Exchange short-lived token for long-lived (60 days)."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(f"{GRAPH_URL}/oauth/access_token", params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": access_token,
        })
        r.raise_for_status()
        return r.json()


async def inspect_token(access_token: str, app_id: str = "", app_secret: str = "") -> dict:
    """Hỏi Facebook xem token này còn sống bao lâu và có những quyền gì.

    Cách duy nhất biết chắc token là loại ngắn hạn (1-2 tiếng) hay dài hạn
    (60 ngày). Không có App ID/Secret thì Facebook không cho tra, khi đó chỉ
    biết token còn dùng được hay không chứ không biết hạn.
    """
    result = {
        "valid": False, "expires_at": None, "days_left": None,
        "hours_left": None, "never_expires": False, "scopes": [],
        "token_type": "", "can_inspect": bool(app_id and app_secret),
        "error": "",
    }

    if not result["can_inspect"]:
        try:
            await validate_token(access_token)
            result["valid"] = True
        except Exception as e:
            result["error"] = str(e)
        return result

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{GRAPH_URL}/debug_token", params={
                "input_token": access_token,
                "access_token": f"{app_id}|{app_secret}",
            })
        data = (r.json() or {}).get("data", {})
    except Exception as e:
        result["error"] = str(e)
        return result

    if data.get("error"):
        result["error"] = data["error"].get("message", "Token không hợp lệ")
        return result

    result["valid"] = bool(data.get("is_valid"))
    result["scopes"] = data.get("scopes", []) or []
    result["token_type"] = data.get("type", "")

    expires = data.get("expires_at", 0) or 0
    if expires == 0:
        # 0 nghĩa là không hết hạn — thường gặp ở Page Access Token
        result["never_expires"] = True
    else:
        try:
            dt = datetime.fromtimestamp(int(expires))
            result["expires_at"] = dt.isoformat()
            delta = dt - datetime.now()
            result["days_left"] = max(0, delta.days)
            result["hours_left"] = max(0, int(delta.total_seconds() // 3600))
        except (ValueError, OSError, OverflowError):
            pass

    return result


#: Hai kiểu token dùng được với tool.
#:   user   — token của một tài khoản Facebook, lấy ở Graph API Explorer.
#:            Sống 1-2 tiếng, phải đổi sang bản 60 ngày bằng App ID + App Secret.
#:   system — token của Người dùng hệ thống (System User) trong Business Manager.
#:            Tạo với Token Expiration = Never thì dùng vĩnh viễn, không phải gia hạn.
TOKEN_TYPES = ("user", "system")


def normalize_token_type(value: str | None) -> str:
    """Chuẩn hoá kiểu token, giá trị lạ thì coi như token thường."""
    v = (value or "").strip().lower()
    return v if v in TOKEN_TYPES else "user"


def is_system_token(value: str | None) -> bool:
    return normalize_token_type(value) == "system"


def _system_token_warning(info: dict) -> str:
    """Cảnh báo riêng cho token System User.

    Token System User đặt Never thì Facebook trả về `expires_at = 0`. Nếu nó lại
    có hạn thì gần như chắc chắn người dùng dán nhầm token thường, hoặc lúc tạo
    đã chọn hạn 60 ngày — báo ngay còn hơn để mai kia đăng bài mới lỗi.
    """
    if info.get("never_expires"):
        return ""
    if not info.get("can_inspect"):
        return ("Chưa nhập App ID / App Secret nên tool chưa kiểm chứng được token "
                "này có vĩnh viễn thật không. Token System User tạo với "
                "Token Expiration = Never thì dùng mãi, không cần làm gì thêm.")
    if not info.get("valid"):
        return ""  # token hỏng đã có chỗ khác báo

    hours = info.get("hours_left")
    days = info.get("days_left")
    when = f"{hours} tiếng" if hours is not None and hours < 48 else f"{days} ngày"
    return (f"Token này CÓ HẠN ({when} nữa là hết) chứ không phải vĩnh viễn. "
            "Nhiều khả năng đây là token thường chứ không phải token System User, "
            "hoặc lúc tạo đã đặt hạn. Vào Business Settings → Người dùng hệ thống → "
            "chọn System User → Tạo mã truy cập mới, và đặt "
            "Token Expiration = Never.")


def _token_lifetime_warning(info: dict) -> str:
    """Câu cảnh báo khi token sắp chết — để người dùng biết ngay lúc thêm."""
    if info.get("never_expires"):
        return ""
    hours = info.get("hours_left")
    if hours is None:
        return ("Không tra được hạn dùng của token vì thiếu App ID / App Secret. "
                "Token lấy từ Graph API Explorer thường chỉ sống 1-2 tiếng — "
                "hãy nhập đủ App ID và App Secret để có token dùng được 60 ngày.")
    if hours <= 24:
        return (f"CẢNH BÁO: token này chỉ còn sống {hours} tiếng nữa rồi hết hạn! "
                "Đây là token ngắn hạn. Kiểm tra lại App ID và App Secret — "
                "nhập đúng thì Facebook mới cấp token 60 ngày.")
    days = info.get("days_left") or 0
    if days <= 7:
        return f"Token chỉ còn {days} ngày. Nên lấy token mới sớm."
    return ""


async def add_account(name: str, access_token: str, app_id: str = "",
                      app_secret: str = "", token_type: str = "user") -> dict:
    """Thêm tài khoản Facebook: kiểm token, đổi sang dài hạn nếu cần, lưu vào DB."""
    user_info = await validate_token(access_token)
    token_type = normalize_token_type(token_type)
    system = token_type == "system"

    final_token = access_token
    expires_at = ""
    exchange_error = ""

    if system:
        # Token System User vốn đã vĩnh viễn. Đem đi đổi sang token "60 ngày"
        # chỉ làm nó ngắn đi — nên bỏ hẳn bước đổi.
        pass
    elif app_id and app_secret:
        try:
            ll = await get_long_lived_token(access_token, app_id, app_secret)
            final_token = ll.get("access_token", access_token)
            expires_in = ll.get("expires_in", 0)
            if expires_in:
                from datetime import timedelta
                expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
        except Exception as e:
            # Trước đây chỉ ghi log rồi giữ token ngắn hạn trong im lặng — người
            # dùng tưởng đã có token 60 ngày, hôm sau đăng bài mới biết token chết.
            log.warning(f"Could not get long-lived token: {e}")
            exchange_error = str(e)
    else:
        exchange_error = "Chưa nhập App ID / App Secret"

    encrypted = encrypt_token(final_token)
    encrypted_app_id = encrypt_token(app_id) if app_id else ""
    encrypted_app_secret = encrypt_token(app_secret) if app_secret else ""

    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO accounts (name, fb_user_id, access_token, fb_app_id,
                                 fb_app_secret, token_expires_at, token_type, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'active')""",
        (name, user_info["id"], encrypted, encrypted_app_id, encrypted_app_secret,
         expires_at, token_type),
    )
    await db.commit()
    account_id = cursor.lastrowid

    # Hỏi Facebook xem token vừa lưu sống được bao lâu, báo ngay nếu quá ngắn
    info = await inspect_token(final_token, app_id, app_secret)

    if system:
        warning = _system_token_warning(info)
    else:
        warning = _token_lifetime_warning(info)
        # Token vĩnh viễn thì việc không đổi được sang bản 60 ngày chẳng hại gì —
        # đừng doạ người dùng bằng cảnh báo của luồng token thường.
        if exchange_error and not warning and not info.get("never_expires"):
            warning = (f"Không đổi được sang token 60 ngày ({exchange_error}). "
                       "Token hiện tại có thể hết hạn sau vài tiếng.")

    return {
        "id": account_id,
        "name": name,
        "fb_user_id": user_info["id"],
        "fb_name": user_info.get("name", ""),
        "status": "active",
        "token_expires_at": expires_at,
        "token_type": token_type,
        "never_expires": bool(info.get("never_expires")),
        "long_lived": system or (bool(expires_at) and not exchange_error),
        "days_left": info.get("days_left"),
        "hours_left": info.get("hours_left"),
        "warning": warning,
    }


async def check_account_token(account_id: int) -> dict:
    """Kiểm tra token của tài khoản còn dùng được không.

    Hỏi thẳng Facebook thay vì chỉ dựa vào ngày hết hạn đã lưu — token có thể chết
    sớm hơn dự kiến khi người dùng đổi mật khẩu hoặc gỡ quyền ứng dụng.
    """
    db = await get_db()
    cursor = await db.execute(
        """SELECT name, token_expires_at, fb_app_id, fb_app_secret,
                  LENGTH(fb_app_secret) AS has_secret,
                  COALESCE(token_type, 'user') AS token_type
           FROM accounts WHERE id = ?""",
        (account_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return {"valid": False, "message": "Không tìm thấy tài khoản"}

    days_left = None
    if row["token_expires_at"]:
        try:
            expires = datetime.fromisoformat(row["token_expires_at"])
            days_left = max(0, (expires - datetime.now()).days)
        except ValueError:
            pass

    app_id = decrypt_token(row["fb_app_id"]) if row["fb_app_id"] else ""
    app_secret = decrypt_token(row["fb_app_secret"]) if row["fb_app_secret"] else ""

    try:
        token = await _get_account_token(account_id)
    except Exception as e:
        return {"valid": False, "message": f"Không đọc được token đã lưu: {e}",
                "account_name": row["name"]}

    info = await inspect_token(token, app_id, app_secret)

    if not info["valid"]:
        return {
            "valid": False,
            "message": explain_fb_error(190, info.get("error") or "Token đã hết hạn"),
            "days_left": None,
            "long_lived": False,
            "account_name": row["name"],
            "can_inspect": info["can_inspect"],
        }

    # Ưu tiên hạn Facebook trả về; chỉ dùng mốc đã lưu khi không tra được
    if info.get("days_left") is not None:
        days_left = info["days_left"]

    system = row["token_type"] == "system"

    if info.get("never_expires"):
        message = ("Token System User — còn dùng được và KHÔNG BAO GIỜ hết hạn."
                   if system else "Token còn dùng được và không có hạn.")
    elif system:
        # Đã khai là System User mà token lại có hạn — gần như chắc chắn dán nhầm
        message = _system_token_warning(info) or "Token còn dùng được."
    elif info.get("hours_left") is not None and info["hours_left"] <= 24:
        message = (f"Token chỉ còn {info['hours_left']} tiếng nữa là hết hạn — "
                   "đây là token NGẮN HẠN. Cần nhập đúng App ID và App Secret "
                   "để lấy token dùng được 60 ngày.")
    elif days_left is not None:
        message = f"Token còn dùng được, hết hạn sau {days_left} ngày."
        if days_left <= 7:
            message += " Nên cập nhật token mới sớm."
    else:
        message = ("Token còn dùng được, nhưng chưa nhập App ID / App Secret nên "
                   "không tra được hạn. Token loại này thường chỉ sống 1-2 tiếng.")

    return {
        "valid": True,
        "message": message,
        "token_type": row["token_type"],
        "days_left": days_left,
        "hours_left": info.get("hours_left"),
        "never_expires": info.get("never_expires", False),
        # `has_secret` la co that su luu App Secret hay khong. Truoc day giao dien
        # doc nham tu `long_lived`, nen tai khoan System User khong co secret van
        # hien "Co App Secret: Co" — trai nguoc voi chinh cau thong bao ben tren.
        "has_secret": bool(row["has_secret"]),
        "long_lived": system or bool(row["has_secret"]),
        "scopes": info.get("scopes", []),
        "account_name": row["name"],
        "can_inspect": info["can_inspect"],
    }


async def update_account_token(
    account_id: int, access_token: str, app_id: str = "", app_secret: str = "",
    token_type: str | None = None,
) -> dict:
    """Thay token cho tài khoản đã có, rồi lấy lại token của toàn bộ Page.

    Page token nằm riêng ở bảng `pages` và được cấp dựa trên token tài khoản lúc
    quét. Nếu chỉ đổi token tài khoản mà không quét lại, các Page vẫn dùng token
    cũ đã chết -> đăng bài lỗi 190 dù token mới hoàn toàn hợp lệ.
    """
    user_info = await validate_token(access_token)

    db = await get_db()
    cursor = await db.execute(
        """SELECT fb_app_id, fb_app_secret, COALESCE(token_type, 'user') AS token_type
           FROM accounts WHERE id = ?""",
        (account_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise ValueError("Không tìm thấy tài khoản")

    # Không chỉ định thì giữ nguyên kiểu token của tài khoản
    token_type = normalize_token_type(token_type or row["token_type"])
    system = token_type == "system"

    # Chưa nhập mới thì dùng lại App ID / Secret đã lưu
    if not app_id and row["fb_app_id"]:
        app_id = decrypt_token(row["fb_app_id"])
    if not app_secret and row["fb_app_secret"]:
        app_secret = decrypt_token(row["fb_app_secret"])

    final_token = access_token
    expires_at = ""
    long_lived = False
    exchange_error = ""
    if system:
        # Token System User đã vĩnh viễn, đổi sang bản 60 ngày chỉ làm nó ngắn đi
        long_lived = True
    elif app_id and app_secret:
        try:
            ll = await get_long_lived_token(access_token, app_id, app_secret)
            final_token = ll.get("access_token", access_token)
            expires_in = ll.get("expires_in", 0)
            if expires_in:
                from datetime import timedelta
                expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
            long_lived = True
        except Exception as e:
            log.warning(f"Không đổi được token dài hạn: {e}")
            exchange_error = str(e)
    else:
        exchange_error = "Chưa nhập App ID / App Secret"

    await db.execute(
        """UPDATE accounts SET access_token = ?, fb_user_id = ?, fb_app_id = ?,
               fb_app_secret = ?, token_expires_at = ?, token_type = ?,
               status = 'active', updated_at = datetime('now')
           WHERE id = ?""",
        (encrypt_token(final_token), user_info["id"],
         encrypt_token(app_id) if app_id else "",
         encrypt_token(app_secret) if app_secret else "",
         expires_at, token_type, account_id),
    )
    await db.commit()

    # Bắt buộc quét lại để mọi Page nhận token mới
    pages = await discover_pages(account_id)

    info = await inspect_token(final_token, app_id, app_secret)
    warning = (_system_token_warning(info) if system
               else _token_lifetime_warning(info))
    if not system and exchange_error and not warning and not info.get("never_expires"):
        warning = (f"Không đổi được sang token 60 ngày ({exchange_error}). "
                   "Token hiện tại có thể hết hạn sau vài tiếng.")

    return {
        "id": account_id,
        "fb_user_id": user_info["id"],
        "fb_name": user_info.get("name", ""),
        "long_lived": long_lived,
        "token_expires_at": expires_at,
        "days_left": info.get("days_left"),
        "hours_left": info.get("hours_left"),
        "pages_refreshed": len(pages),
        "token_type": token_type,
        "never_expires": bool(info.get("never_expires")),
        "warning": warning,
    }


async def get_accounts() -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        """SELECT id, name, fb_user_id, token_expires_at, status, created_at,
                  COALESCE(token_type, 'user') AS token_type
           FROM accounts ORDER BY id DESC"""
    )
    rows = await cursor.fetchall()

    result = []
    for row in rows:
        pc = await db.execute("SELECT COUNT(*) as cnt FROM pages WHERE account_id = ?", (row["id"],))
        page_row = await pc.fetchone()

        result.append({
            "id": row["id"],
            "name": row["name"],
            "fb_user_id": row["fb_user_id"],
            "token_expires_at": row["token_expires_at"],
            "token_type": row["token_type"],
            "status": row["status"],
            "pages_count": page_row["cnt"],
            "created_at": row["created_at"],
        })
    return result


async def delete_account(account_id: int) -> bool:
    db = await get_db()
    await db.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    await db.commit()
    return True


async def _get_account_token(account_id: int) -> str:
    db = await get_db()
    cursor = await db.execute("SELECT access_token FROM accounts WHERE id = ?", (account_id,))
    row = await cursor.fetchone()
    if not row:
        raise ValueError(f"Account {account_id} not found")
    return decrypt_token(row["access_token"])


# ── Page Management ──────────────────────────────────────────

#: Các trường cần lấy về cho mỗi Page
_PAGE_FIELDS = "id,name,category,access_token,followers_count,picture{url}"


async def _graph_list(client: httpx.AsyncClient, path: str, token: str,
                      fields: str = _PAGE_FIELDS) -> tuple[list[dict], str]:
    """Gọi một edge trả về danh sách. Trả (danh sách, lỗi) — lỗi rỗng là ổn."""
    try:
        r = await client.get(f"{GRAPH_URL}/{path}", params={
            "access_token": token, "fields": fields, "limit": 200,
        })
        data = r.json() or {}
    except Exception as e:
        return [], str(e)

    if isinstance(data.get("error"), dict):
        err = data["error"]
        return [], err.get("message", "Lỗi không rõ")
    return data.get("data", []) or [], ""


async def _page_token(client: httpx.AsyncClient, page_id: str, token: str) -> str:
    """Xin token riêng của một Page. Page lấy từ Business không kèm sẵn token."""
    try:
        r = await client.get(f"{GRAPH_URL}/{page_id}", params={
            "access_token": token, "fields": "access_token",
        })
        return (r.json() or {}).get("access_token", "") or ""
    except Exception as e:
        log.warning("Không lấy được token của Page %s: %s", page_id, e)
        return ""


async def fetch_managed_pages(token: str) -> tuple[list[dict], list[str]]:
    """Danh sách Page mà token này quản lý, kèm nhật ký các bước đã thử.

    Token thường: `/me/accounts` là đủ.

    Token System User thì KHÁC HẲN: System User không "sở hữu" Page theo kiểu cá
    nhân, Page được GÁN cho nó trong Business. Vì vậy `/me/accounts` gần như luôn
    trả về rỗng — đó là lý do thêm token System User vào mà không thấy Page nào.
    Phải hỏi thêm `assigned_pages` của chính System User, rồi tới các Page mà
    Business sở hữu hoặc được cấp quyền.
    """
    found: dict[str, dict] = {}
    steps: list[str] = []

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # ── 1. Cách thường: Page của chính tài khoản ──────
        pages, err = await _graph_list(client, "me/accounts", token)
        steps.append(f"me/accounts: {len(pages)} Page" + (f" — {err}" if err else ""))
        for p in pages:
            found[p["id"]] = p

        # ── 2. Page được gán cho System User ──────────────
        if not found:
            me_id = ""
            try:
                r = await client.get(f"{GRAPH_URL}/me",
                                     params={"access_token": token, "fields": "id,name"})
                me_id = (r.json() or {}).get("id", "") or ""
            except Exception as e:
                steps.append(f"me: {e}")

            if me_id:
                pages, err = await _graph_list(client, f"{me_id}/assigned_pages", token)
                steps.append(f"assigned_pages: {len(pages)} Page"
                             + (f" — {err}" if err else ""))
                for p in pages:
                    found[p["id"]] = p

        # ── 3. Page thuộc Business ────────────────────────
        if not found:
            businesses, err = await _graph_list(client, "me/businesses", token, "id,name")
            steps.append(f"me/businesses: {len(businesses)} Business"
                         + (f" — {err}" if err else ""))
            for biz in businesses:
                for edge in ("owned_pages", "client_pages"):
                    pages, err = await _graph_list(client, f"{biz['id']}/{edge}", token)
                    steps.append(f"{biz.get('name', biz['id'])}/{edge}: {len(pages)} Page"
                                 + (f" — {err}" if err else ""))
                    for p in pages:
                        found.setdefault(p["id"], p)

        # ── Page lấy từ Business không kèm token, phải xin riêng ──
        for pid, p in found.items():
            if not p.get("access_token"):
                p["access_token"] = await _page_token(client, pid, token)

    usable = [p for p in found.values() if p.get("access_token")]
    thieu = len(found) - len(usable)
    if thieu:
        steps.append(f"{thieu} Page tìm thấy nhưng không xin được token riêng "
                     f"(thường do System User chưa được cấp Toàn quyền trên Page đó)")

    return usable, steps


def explain_no_pages(steps: list[str], token_type: str) -> str:
    """Câu giải thích khi quét xong mà không ra Page nào."""
    chung = " | ".join(steps)
    if token_type == "system":
        return (
            "Không tìm thấy Fanpage nào cho token System User này. Kiểm tra lần lượt:\n"
            "1. Business Settings → Người dùng hệ thống → chọn System User → "
            "Thêm tài sản → Trang → tích Fanpage → bật TOÀN QUYỀN (Full control). "
            "Chỉ 'Xem' hoặc 'Tạo nội dung' là không đăng bài được.\n"
            "2. Lúc tạo token phải tích đủ quyền: pages_show_list, "
            "pages_manage_posts, pages_read_engagement, publish_video, business_management.\n"
            "3. App phải nằm trong Business: Business Settings → Tài khoản → Ứng dụng.\n"
            "4. Chính Fanpage cũng phải thuộc Business: Business Settings → Tài khoản → Trang.\n\n"
            f"Tool đã hỏi Facebook: {chung}"
        )
    return (
        "Không tìm thấy Fanpage nào. Kiểm tra:\n"
        "1. Tài khoản này có đang là quản trị viên của Fanpage nào không.\n"
        "2. Lúc lấy token đã tích quyền pages_show_list và pages_manage_posts chưa.\n"
        "3. Nếu vừa được thêm làm quản trị viên thì lấy lại token mới.\n\n"
        f"Tool đã hỏi Facebook: {chung}"
    )


async def discover_pages_detailed(account_id: int) -> dict:
    """Quét Fanpage và trả kèm nhật ký các bước — để giải thích khi không ra Page nào."""
    token = await _get_account_token(account_id)
    pages, steps = await fetch_managed_pages(token)
    log.info("Quét Page cho tài khoản %s: %s", account_id, " | ".join(steps))

    db = await get_db()
    saved = []
    for page in pages:
        page_token = encrypt_token(page["access_token"])
        avatar = ""
        if "picture" in page and isinstance(page["picture"], dict):
            avatar = (page["picture"].get("data") or {}).get("url", "")

        await db.execute(
            """INSERT INTO pages (account_id, fb_page_id, page_name, page_access_token, category, avatar_url, followers_count, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
               ON CONFLICT(fb_page_id) DO UPDATE SET
                   page_name = excluded.page_name,
                   page_access_token = excluded.page_access_token,
                   category = excluded.category,
                   avatar_url = excluded.avatar_url,
                   followers_count = excluded.followers_count,
                   updated_at = datetime('now')""",
            (account_id, page["id"], page.get("name", ""), page_token,
             page.get("category", ""), avatar, page.get("followers_count", 0)),
        )
        saved.append({
            "fb_page_id": page["id"],
            "page_name": page.get("name", ""),
            "category": page.get("category", ""),
            "followers_count": page.get("followers_count", 0),
            "avatar_url": avatar,
        })
    await db.commit()
    return {"pages": saved, "steps": steps}


async def discover_pages(account_id: int) -> list[dict]:
    """Quét toàn bộ Fanpage của một tài khoản rồi lưu vào DB."""
    return (await discover_pages_detailed(account_id))["pages"]


async def get_pages(account_id: int | None = None, status: str | None = None) -> list[dict]:
    db = await get_db()
    query = """SELECT p.*, a.name as account_name
               FROM pages p JOIN accounts a ON p.account_id = a.id WHERE 1=1"""
    params = []
    if account_id:
        query += " AND p.account_id = ?"
        params.append(account_id)
    if status:
        query += " AND p.status = ?"
        params.append(status)
    query += " ORDER BY p.page_name ASC"

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    result = []
    for row in rows:
        pc = await db.execute("SELECT COUNT(*) as cnt FROM posts WHERE page_id = ?", (row["id"],))
        post_row = await pc.fetchone()

        vc = await db.execute("SELECT COALESCE(SUM(views_count), 0) as total FROM posts WHERE page_id = ?", (row["id"],))
        views_row = await vc.fetchone()

        # Use the larger of: direct page total_views (from sync) vs SUM of post views
        page_total = row["total_views"] if "total_views" in row.keys() else 0
        posts_total = views_row["total"]
        best_views = max(page_total or 0, posts_total or 0)

        result.append({
            "id": row["id"],
            "account_id": row["account_id"],
            "account_name": row["account_name"],
            "fb_page_id": row["fb_page_id"],
            "page_name": row["page_name"],
            "category": row["category"],
            "avatar_url": row["avatar_url"],
            "store_url": row["store_url"],
            "followers_count": row["followers_count"],
            "status": row["status"],
            "posts_count": post_row["cnt"],
            "total_views": best_views,
            "created_at": row["created_at"],
        })
    return result


async def update_page(page_id: int, store_url: str = None, comment_templates: list = None, status: str = None) -> dict:
    db = await get_db()
    updates = []
    params = []
    if store_url is not None:
        updates.append("store_url = ?")
        params.append(store_url)
    if comment_templates is not None:
        updates.append("comment_templates = ?")
        params.append(json.dumps(comment_templates, ensure_ascii=False))
    if status is not None:
        updates.append("status = ?")
        params.append(status)

    updates.append("updated_at = datetime('now')")
    params.append(page_id)

    await db.execute(f"UPDATE pages SET {', '.join(updates)} WHERE id = ?", params)
    await db.commit()

    cursor = await db.execute("SELECT * FROM pages WHERE id = ?", (page_id,))
    row = await cursor.fetchone()
    return dict(row) if row else {}


async def _get_page_token(page_id: int) -> tuple[str, str]:
    """Return (decrypted page token, fb_page_id)."""
    db = await get_db()
    cursor = await db.execute("SELECT page_access_token, fb_page_id FROM pages WHERE id = ?", (page_id,))
    row = await cursor.fetchone()
    if not row:
        raise ValueError(f"Page {page_id} not found")
    return decrypt_token(row["page_access_token"]), row["fb_page_id"]

# ── Page Metrics Sync ────────────────────────────────────────

async def sync_page_metrics(page_id: int) -> dict:
    """Fetch live metrics for a page from Facebook Graph API."""
    token, fb_page_id = await _get_page_token(page_id)

    all_videos = []  # Collect all video data for post matching

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # 1. Page basic info (followers)
        r = await client.get(f"{GRAPH_URL}/{fb_page_id}", params={
            "access_token": token,
            "fields": "id,name,followers_count,fan_count",
        })
        page_data = r.json() if r.status_code == 200 else {}
        followers = page_data.get("followers_count", page_data.get("fan_count", 0))

        # 2. Reels — list endpoint supports basic fields
        r2 = await client.get(f"{GRAPH_URL}/{fb_page_id}/video_reels", params={
            "access_token": token,
            "fields": "id,description,views,created_time",
            "limit": 50,
        })
        reels_data = r2.json().get("data", []) if r2.status_code == 200 else []
        for v in reels_data:
            all_videos.append({
                "fb_id": v.get("id", ""),
                "views": v.get("views", 0),
                "description": v.get("description", ""),
                "created_time": v.get("created_time", ""),
                "post_type": "reel",
                "likes": 0, "comments": 0, "shares": 0,
            })

        # 3. Regular videos
        r3 = await client.get(f"{GRAPH_URL}/{fb_page_id}/videos", params={
            "access_token": token,
            "fields": "id,views,description,created_time",
            "limit": 50,
        })
        reg_videos = r3.json().get("data", []) if r3.status_code == 200 else []
        seen_ids = {v["fb_id"] for v in all_videos}
        for v in reg_videos:
            vid = v.get("id", "")
            if vid not in seen_ids:
                all_videos.append({
                    "fb_id": vid,
                    "views": v.get("views", 0),
                    "description": v.get("description", ""),
                    "created_time": v.get("created_time", ""),
                    "post_type": "video",
                    "likes": 0, "comments": 0, "shares": 0,
                })

        # 4. Fetch engagement per-video (likes, comments via direct fields; shares via video_insights)
        try:
            import asyncio

            async def _fetch_video_engagement(client: httpx.AsyncClient, vid_id: str) -> dict:
                """Fetch likes, comments, and shares for a single video."""
                eng = {"likes": 0, "comments": 0, "shares": 0}
                try:
                    # Get likes + comments in one call
                    r = await client.get(f"{GRAPH_URL}/{vid_id}", params={
                        "access_token": token,
                        "fields": "likes.summary(true),comments.summary(true)",
                    })
                    if r.status_code == 200:
                        data = r.json()
                        eng["likes"] = data.get("likes", {}).get("summary", {}).get("total_count", 0)
                        eng["comments"] = data.get("comments", {}).get("summary", {}).get("total_count", 0)

                    # Get shares from video_insights
                    r2 = await client.get(f"{GRAPH_URL}/{vid_id}/video_insights", params={
                        "access_token": token,
                        "metric": "post_video_social_actions",
                    })
                    if r2.status_code == 200:
                        for insight in r2.json().get("data", []):
                            if insight.get("name") == "post_video_social_actions":
                                values = insight.get("values", [{}])
                                if values:
                                    eng["shares"] = values[0].get("value", {}).get("SHARE", 0)
                except Exception:
                    pass
                return eng

            videos_with_ids = [v for v in all_videos if v["fb_id"]]
            if videos_with_ids:
                async with httpx.AsyncClient(timeout=TIMEOUT) as eng_client:
                    # Process in batches of 10 to avoid rate limits
                    batch_size = 10
                    for i in range(0, len(videos_with_ids), batch_size):
                        batch = videos_with_ids[i:i + batch_size]
                        tasks = [_fetch_video_engagement(eng_client, v["fb_id"]) for v in batch]
                        results = await asyncio.gather(*tasks)
                        for v, eng in zip(batch, results):
                            v["likes"] = eng["likes"]
                            v["comments"] = eng["comments"]
                            v["shares"] = eng["shares"]

                matched = sum(1 for v in all_videos if v["likes"] > 0 or v["comments"] > 0 or v["shares"] > 0)
                logger.info(f"Engagement fetched: {matched}/{len(all_videos)} videos with engagement for page {fb_page_id}")
        except Exception as e:
            logger.warning(f"Engagement fetch failed: {e}")

    # Calculate totals
    total_views = sum(v["views"] for v in all_videos)
    top_video = max(all_videos, key=lambda x: x["views"]) if all_videos else {"fb_id": "", "views": 0}

    db = await get_db()

    # Update page: followers + total_views
    await db.execute(
        "UPDATE pages SET followers_count = ?, total_views = ?, updated_at = datetime('now') WHERE id = ?",
        (followers, total_views, page_id),
    )

    # Cross-match: update views for posts already in DB + check viral thresholds
    from backend.database import get_setting as _get_setting
    from backend.services.telegram import send_viral_alert as _send_viral_alert

    viral_thresholds = {
        "catching": int(await _get_setting("viral_threshold_catching", "10000")),
        "viral": int(await _get_setting("viral_threshold_viral", "100000")),
        "super_viral": int(await _get_setting("viral_threshold_super_viral", "1000000")),
    }

    def _classify(views: int) -> str | None:
        if views >= viral_thresholds["super_viral"]:
            return "super_viral"
        if views >= viral_thresholds["viral"]:
            return "viral"
        if views >= viral_thresholds["catching"]:
            return "catching"
        return None

    posts_updated = 0
    posts_inserted = 0
    new_posts_list = []  # Collect newly discovered posts for Telegram alert
    for v in all_videos:
        if not v["fb_id"]:
            continue
        cursor = await db.execute(
            "SELECT id, viral_level, views_count FROM posts WHERE page_id = ? AND fb_post_id = ?",
            (page_id, v["fb_id"]),
        )
        post_row = await cursor.fetchone()

        if not post_row:
            # ── AUTO-INSERT: New post discovered from Facebook ──
            # Parse created_time from FB (ISO format) to local format
            posted_at = ""
            if v.get("created_time"):
                try:
                    from datetime import datetime as _dt
                    dt = _dt.fromisoformat(v["created_time"].replace("Z", "+00:00"))
                    posted_at = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    posted_at = v["created_time"]

            insert_cursor = await db.execute(
                """INSERT INTO posts
                   (page_id, fb_post_id, post_type, caption, status, posted_at,
                    views_count, likes_count, comments_count, shares_count,
                    viral_level, last_checked_at)
                   VALUES (?, ?, ?, ?, 'posted', ?, ?, ?, ?, ?, 'none', datetime('now'))""",
                (
                    page_id,
                    v["fb_id"],
                    v.get("post_type", "reel"),
                    v.get("description", ""),
                    posted_at,
                    v["views"],
                    v.get("likes", 0),
                    v.get("comments", 0),
                    v.get("shares", 0),
                ),
            )
            posts_inserted += 1
            post_id_new = insert_cursor.lastrowid
            log.info(f"Auto-inserted new post from FB: fb_id={v['fb_id']}, views={v['views']}, type={v.get('post_type')}")
            new_posts_list.append({
                "fb_id": v["fb_id"],
                "views": v["views"],
                "description": v.get("description", ""),
                "post_type": v.get("post_type", "reel"),
                "posted_at": posted_at,
            })

            # Check viral level for newly inserted post
            new_level = _classify(v["views"])
            if new_level:
                await db.execute("UPDATE posts SET viral_level = ? WHERE id = ?", (new_level, post_id_new))
            continue

        # ── UPDATE existing post ──
        if post_row:
            await db.execute(
                """UPDATE posts SET views_count = ?, likes_count = ?, comments_count = ?, shares_count = ?,
                   last_checked_at = datetime('now') WHERE id = ?""",
                (v["views"], v.get("likes", 0), v.get("comments", 0), v.get("shares", 0), post_row["id"]),
            )
            posts_updated += 1

            # Check viral level and trigger alert if threshold crossed
            new_level = _classify(v["views"])
            old_level = post_row["viral_level"]
            if new_level and new_level != old_level:
                await db.execute(
                    "UPDATE posts SET viral_level = ? WHERE id = ?",
                    (new_level, post_row["id"]),
                )
                # Insert viral_alerts record if not exists
                existing = await db.execute(
                    "SELECT id FROM viral_alerts WHERE post_id = ? AND level = ?",
                    (post_row["id"], new_level),
                )
                if not await existing.fetchone():
                    await db.execute(
                        """INSERT INTO viral_alerts (post_id, level, views_at_alert, telegram_sent)
                           VALUES (?, ?, ?, 0)""",
                        (post_row["id"], new_level, v["views"]),
                    )
                    await db.commit()

                    # Send Telegram alert
                    alert_data = {
                        "page_name": page_data.get("name", "N/A"),
                        "views_count": v["views"],
                        "likes_count": v.get("likes", 0),
                        "comments_count": v.get("comments", 0),
                        "shares_count": v.get("shares", 0),
                        "store_url": "",
                        "fb_post_id": v["fb_id"],
                    }
                    try:
                        tg_sent = await _send_viral_alert(alert_data, new_level)
                        if tg_sent:
                            await db.execute(
                                "UPDATE viral_alerts SET telegram_sent = 1 WHERE post_id = ? AND level = ?",
                                (post_row["id"], new_level),
                            )
                    except Exception as tg_err:
                        log.error(f"Telegram viral alert failed for post {post_row['id']}: {tg_err}")

                log.info(f"Post {post_row['id']} crossed viral level: {old_level} -> {new_level} ({v['views']} views)")

    # Count posts for this page
    pc = await db.execute("SELECT COUNT(*) as cnt FROM posts WHERE page_id = ?", (page_id,))
    post_count = (await pc.fetchone())["cnt"]

    metrics = {
        "page_id": page_id,
        "followers_count": followers,
        "daily_views": total_views,
        "daily_reach": 0,
        "total_posts": post_count,
        "top_video_id": top_video["fb_id"],
        "top_video_views": top_video["views"],
        "posts_synced": posts_updated,
        "posts_inserted": posts_inserted,
    }

    # Save to history
    await db.execute(
        """INSERT INTO page_metrics_history
           (page_id, followers_count, daily_views, daily_reach, total_posts, top_video_id, top_video_views)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (page_id, followers, total_views, 0, post_count, top_video["fb_id"], top_video["views"]),
    )
    await db.commit()

    # Send Telegram alert only for posts published TODAY
    if new_posts_list:
        from datetime import date as _date
        today_str = _date.today().strftime("%Y-%m-%d")
        today_posts = [p for p in new_posts_list if p.get("posted_at", "").startswith(today_str)]
        if today_posts:
            try:
                from backend.services.telegram import send_new_posts_alert
                await send_new_posts_alert(page_data.get("name", f"Page #{page_id}"), today_posts)
            except Exception as e:
                log.error(f"Telegram new posts alert failed: {e}")
        else:
            log.info(f"Skipped Telegram alert: {len(new_posts_list)} new posts found but none from today ({today_str})")

    log.info(f"Synced page {page_id}: followers={followers}, views={total_views}, posts_synced={posts_updated}, posts_inserted={posts_inserted}")
    return metrics


# ── Reels Publishing ─────────────────────────────────────────


#: Quyền tối thiểu để đăng Reel lên Page
REQUIRED_PAGE_SCOPES = ["pages_show_list", "pages_read_engagement", "pages_manage_posts"]


async def diagnose_page_permissions(page_id: int) -> str:
    """Tìm lý do thật khi Facebook báo thiếu quyền.

    Cấp quyền cho ứng dụng xong mà vẫn lỗi là chuyện rất hay gặp: token của Page
    được cấp tại thời điểm quét Fanpage, nên nó giữ đúng bộ quyền của lúc đó.
    Cấp thêm quyền sau mà không quét lại thì Page vẫn dùng token cũ thiếu quyền.
    """
    db = await get_db()
    cursor = await db.execute(
        """SELECT p.page_name, p.account_id, a.fb_app_id, a.fb_app_secret
           FROM pages p LEFT JOIN accounts a ON a.id = p.account_id
           WHERE p.id = ?""",
        (page_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return ""

    app_id = decrypt_token(row["fb_app_id"]) if row["fb_app_id"] else ""
    app_secret = decrypt_token(row["fb_app_secret"]) if row["fb_app_secret"] else ""

    try:
        page_token, _ = await _get_page_token(page_id)
        info = await inspect_token(page_token, app_id, app_secret)
    except Exception as e:
        return f"Không kiểm tra được token của Page: {e}"

    if not info.get("can_inspect"):
        return ("Chưa nhập App ID / App Secret nên không tra được quyền của Page. "
                "Vào Tài Khoản, bấm 'Cập nhật token' và nhập đủ hai ô đó.")

    scopes = info.get("scopes") or []
    missing = [s for s in REQUIRED_PAGE_SCOPES if s not in scopes]

    if missing:
        return (
            f"Token của Page '{row['page_name']}' đang THIẾU quyền: {', '.join(missing)}.\n"
            f"Quyền hiện có: {', '.join(scopes) if scopes else '(không có quyền nào)'}\n\n"
            "Nguyên nhân thường gặp: đã cấp thêm quyền cho ứng dụng NHƯNG chưa quét lại Fanpage.\n"
            "Token của mỗi Page được cấp lúc quét, nên phải quét lại thì Page mới nhận quyền mới.\n"
            "Cách sửa: vào Tài Khoản → bấm 'Cập nhật token' (nút này tự quét lại toàn bộ Page)."
        )

    return (
        f"Token của Page '{row['page_name']}' ĐÃ CÓ đủ quyền: {', '.join(REQUIRED_PAGE_SCOPES)}.\n"
        "Vậy vấn đề nằm ở phía ứng dụng Facebook, thường là một trong các lý do sau:\n"
        "1. Ứng dụng đang ở chế độ Development — chỉ đăng được lên Page mà tài khoản của bạn\n"
        "   là quản trị viên. Vào Facebook Developer → App → chuyển sang chế độ Live.\n"
        "2. Ứng dụng chưa qua App Review cho quyền pages_manage_posts.\n"
        "3. Tài khoản Facebook không còn là quản trị viên của Page này.\n"
        "4. Page bị hạn chế đăng bài — kiểm tra Chất lượng Trang trên Facebook."
    )


async def publish_reel(page_id: int, video_path: str, caption: str = "") -> dict:
    """Upload and publish a Reel to a Facebook Page.
    
    Strategy: Try video_reels endpoint first (3-step).
    If it fails with checkpoint/identity error, fallback to /videos endpoint.
    """
    token, fb_page_id = await _get_page_token(page_id)
    from pathlib import Path

    log.info(f"publish_reel START: page_id={page_id}, fb_page_id={fb_page_id}, file={video_path}")

    # ── Method 1: video_reels (3-step) ───────────────────────
    method1_error = None
    try:
        result = await _publish_reel_3step(token, fb_page_id, video_path, caption)
        log.info(f"publish_reel SUCCESS via video_reels: {result}")
        return result
    except Exception as e:
        method1_error = str(e)
        err_str = method1_error.lower()
        # Only fallback on checkpoint/identity errors
        if "confirm your identity" in err_str or "368" in method1_error or "4854002" in method1_error:
            log.warning(f"video_reels blocked by checkpoint, trying /videos fallback: {e}")
        else:
            log.error(f"video_reels failed (non-checkpoint): {e}")
            # Lỗi thiếu quyền: kiểm tra token thật rồi nói rõ nguyên nhân, thay vì
            # chỉ khuyên "cấp thêm quyền" trong khi người dùng đã cấp đủ từ trước
            if "thiếu quyền" in method1_error or "permission" in err_str:
                try:
                    detail = await diagnose_page_permissions(page_id)
                    if detail:
                        raise ValueError(f"{method1_error}\n\n── Kiểm tra thực tế ──\n{detail}")
                except ValueError:
                    raise
                except Exception as diag_err:
                    log.warning(f"Chẩn đoán quyền thất bại: {diag_err}")
            raise  # Re-raise non-checkpoint errors

    # ── Method 2: /videos fallback (multipart upload) ────────
    log.info(f"Fallback: publishing via /videos endpoint for page {fb_page_id}")
    try:
        result = await _publish_video_fallback(token, fb_page_id, video_path, caption)
        log.info(f"publish_reel SUCCESS via /videos fallback: {result}")
        return result
    except Exception as e2:
        log.error(f"BOTH methods failed! Method1={method1_error} | Method2={e2}")
        raise ValueError(f"All publish methods failed. video_reels: {method1_error} | /videos: {e2}")


def explain_fb_error(code: int | str, message: str, subcode: int | str = "") -> str:
    """Dịch lỗi Graph API sang tiếng Việt kèm cách xử lý.

    Thông báo gốc của Facebook toàn tiếng Anh kỹ thuật, nhân sự đọc không biết
    phải làm gì — nhất là lỗi token hết hạn, vốn là lỗi hay gặp nhất.
    """
    try:
        code = int(code)
    except (TypeError, ValueError):
        code = 0
    try:
        subcode = int(subcode)
    except (TypeError, ValueError):
        subcode = 0

    if code == 190:
        base = "Token Facebook đã hết hạn hoặc không còn hiệu lực."
        if subcode == 458:
            base = "Bạn đã gỡ quyền của ứng dụng trên Facebook."
        elif subcode == 460:
            base = "Mật khẩu Facebook đã đổi nên token cũ bị vô hiệu."
        elif subcode == 463:
            base = "Token đã hết hạn."
        return (
            f"{base}\n"
            "Cách xử lý:\n"
            "1. Vào mục Tài Khoản, bấm 'Cập nhật token' ở tài khoản này\n"
            "2. Dán User Access Token mới, PHẢI nhập cả App ID và App Secret\n"
            "   (thiếu hai ô này thì token chỉ sống 1-2 tiếng rồi chết)\n"
            "3. Bấm 'Quét Fanpage' để lấy token mới cho từng Page\n"
            "Xem hướng dẫn chi tiết ở mục Lỗi thường gặp trong file HUONG-DAN-SU-DUNG.md"
        )

    if code == 200 or code == 10:
        return ("Ứng dụng Facebook thiếu quyền đăng bài lên Page.\n"
                "Cần quyền: pages_manage_posts, pages_read_engagement, pages_show_list.\n"
                "Vào Facebook Developer -> App -> Permissions để cấp thêm.")

    if code == 368:
        return ("Page đang bị Facebook tạm khoá đăng bài (do vi phạm hoặc đăng quá nhiều).\n"
                "Chờ vài giờ rồi thử lại, hoặc kiểm tra Chất lượng Trang trên Facebook.")

    if code == 100:
        return (f"Facebook từ chối dữ liệu gửi lên: {message}\n"
                "Thường do video sai định dạng hoặc caption chứa ký tự lạ.")

    if code in (4, 17, 32, 613):
        return ("Đã gọi Facebook quá nhiều lần trong thời gian ngắn.\n"
                "Chờ 15-30 phút rồi đăng lại, hoặc giãn cách giữa các page ra xa hơn.")

    if code == 1363030 or "identity" in message.lower():
        return ("Facebook yêu cầu xác minh danh tính cho Page này.\n"
                "Mở ứng dụng Facebook trên điện thoại và làm theo hướng dẫn xác minh.")

    return f"Facebook báo lỗi ({code}): {message}"


async def _publish_reel_3step(token: str, fb_page_id: str, video_path: str, caption: str) -> dict:
    """3-step video_reels upload (init → binary → finish)."""
    from pathlib import Path

    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=30.0)) as client:
        # Step 1: Initialize upload
        init_r = await client.post(
            f"{GRAPH_URL}/{fb_page_id}/video_reels",
            params={"access_token": token},
            json={"upload_phase": "start"},
        )
        if init_r.status_code != 200:
            fb_err = init_r.json().get("error", {})
            err_msg = fb_err.get("message", init_r.text)
            err_code = fb_err.get("code", init_r.status_code)
            err_sub = fb_err.get("error_subcode", "")
            log.error(f"FB init upload failed: code={err_code} sub={err_sub} msg={err_msg}")
            raise ValueError(explain_fb_error(err_code, err_msg, err_sub))
        video_id = init_r.json().get("video_id")
        if not video_id:
            raise ValueError("Failed to initialize reel upload")

        # Step 2: Upload video binary
        video_file = Path(video_path)
        file_size = video_file.stat().st_size

        with open(video_path, "rb") as f:
            upload_r = await client.post(
                f"https://rupload.facebook.com/video-upload/v25.0/{video_id}",
                headers={
                    "Authorization": f"OAuth {token}",
                    "offset": "0",
                    "file_size": str(file_size),
                    "Content-Type": "application/octet-stream",
                },
                content=f.read(),
            )
            upload_r.raise_for_status()

        # Step 3: Publish
        import asyncio as _aio
        max_retries = 2
        publish_r = None
        for attempt in range(max_retries):
            publish_r = await client.post(
                f"{GRAPH_URL}/{fb_page_id}/video_reels",
                params={"access_token": token},
                json={
                    "upload_phase": "finish",
                    "video_id": video_id,
                    "video_state": "PUBLISHED",
                    "description": caption,
                },
            )
            if publish_r.status_code == 200:
                break
            fb_err = publish_r.json().get("error", {})
            err_code = fb_err.get("code", publish_r.status_code)
            err_sub = fb_err.get("error_subcode", "")
            err_msg = fb_err.get("message", publish_r.text)
            log.warning(f"FB publish attempt {attempt+1}/{max_retries}: code={err_code} sub={err_sub} msg={err_msg}")
            if attempt < max_retries - 1:
                await _aio.sleep(5)

        if publish_r.status_code != 200:
            fb_err = publish_r.json().get("error", {})
            err_code = fb_err.get("code", publish_r.status_code)
            err_sub = fb_err.get("error_subcode", "")
            err_msg = fb_err.get("message", publish_r.text)
            raise ValueError(f"Facebook Publish Error ({err_code}/{err_sub}): {err_msg}")

        result = publish_r.json()
        log.info(f"Reel published via video_reels: video_id={video_id} result={result}")

    return {
        "video_id": video_id,
        "fb_post_id": result.get("id", video_id),
        "success": result.get("success", True),
    }


async def _publish_video_fallback(token: str, fb_page_id: str, video_path: str, caption: str) -> dict:
    """Fallback: publish via /videos endpoint (multipart file upload).
    
    This method is more reliable for pages with checkpoint restrictions.
    Videos uploaded here also appear as Reels on mobile if vertical format.
    """
    from pathlib import Path
    video_file = Path(video_path)
    
    if not video_file.exists():
        raise ValueError(f"Video file not found: {video_path}")
    
    file_size = video_file.stat().st_size
    log.info(f"/videos fallback: uploading {video_file.name} ({file_size} bytes) to page {fb_page_id}")

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=30.0)) as client:
            with open(video_path, "rb") as f:
                files = {"source": (video_file.name, f, "video/mp4")}
                data = {
                    "description": caption,
                    "access_token": token,
                }
                r = await client.post(
                    f"https://graph-video.facebook.com/v25.0/{fb_page_id}/videos",
                    data=data,
                    files=files,
                )

            log.info(f"/videos fallback response: status={r.status_code} body={r.text[:500]}")

            if r.status_code != 200:
                try:
                    fb_err = r.json().get("error", {})
                    err_code = fb_err.get("code", r.status_code)
                    err_sub = fb_err.get("error_subcode", "")
                    err_msg = fb_err.get("message", r.text)
                except Exception:
                    err_code = r.status_code
                    err_sub = ""
                    err_msg = r.text[:500]
                log.error(f"FB /videos fallback failed: code={err_code} sub={err_sub} msg={err_msg}")
                raise ValueError(f"Facebook Video Upload Error ({err_code}/{err_sub}): {err_msg}")

            result = r.json()
            video_id = result.get("id", "")
            log.info(f"Video published via /videos fallback: id={video_id}")

        return {
            "video_id": video_id,
            "fb_post_id": video_id,
            "success": True,
        }
    except httpx.HTTPError as he:
        log.error(f"/videos fallback HTTP error: {type(he).__name__}: {he}")
        raise ValueError(f"HTTP connection error during video upload: {he}")


# ── Insights ─────────────────────────────────────────────────

async def get_post_insights(page_id: int, fb_post_id: str) -> dict:
    """Get views, likes, comments, shares for a post."""
    token, _ = await _get_page_token(page_id)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(f"{GRAPH_URL}/{fb_post_id}", params={
            "access_token": token,
            "fields": "id,views,likes.summary(true),comments.summary(true),shares",
        })
        if r.status_code != 200:
            return {}
        data = r.json()

    return {
        "views": data.get("views", 0),
        "likes": data.get("likes", {}).get("summary", {}).get("total_count", 0),
        "comments": data.get("comments", {}).get("summary", {}).get("total_count", 0),
        "shares": data.get("shares", {}).get("count", 0),
    }


async def get_reel_insights(page_id: int, fb_video_id: str) -> dict:
    """Get video/reel specific insights (views, plays)."""
    token, _ = await _get_page_token(page_id)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(f"{GRAPH_URL}/{fb_video_id}", params={
            "access_token": token,
            "fields": "id,description,views,likes.summary(true),comments.summary(true),shares,video_insights.metric(total_video_views,total_video_impressions)",
        })
        if r.status_code != 200:
            return {}
        data = r.json()

    views = data.get("views", 0)
    insights = data.get("video_insights", {}).get("data", [])
    for insight in insights:
        if insight.get("name") == "total_video_views":
            values = insight.get("values", [])
            if values:
                views = max(views, values[0].get("value", 0))

    return {
        "views": views,
        "likes": data.get("likes", {}).get("summary", {}).get("total_count", 0),
        "comments": data.get("comments", {}).get("summary", {}).get("total_count", 0),
        "shares": data.get("shares", {}).get("count", 0),
    }


# ── Comment ──────────────────────────────────────────────────

async def post_comment(page_id: int, fb_post_id: str, message: str, attachment_url: str = "") -> dict:
    """Post a comment on a page post (using page token). Supports image attachment."""
    token, _ = await _get_page_token(page_id)

    payload = {"message": message}
    if attachment_url:
        payload["attachment_url"] = attachment_url

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{GRAPH_URL}/{fb_post_id}/comments", params={
            "access_token": token,
        }, json=payload)
        r.raise_for_status()
        return r.json()
