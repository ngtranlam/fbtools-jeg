"""API routes for Facebook account management."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services import facebook

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


class AddAccountRequest(BaseModel):
    name: str
    access_token: str
    app_id: str = ""
    app_secret: str = ""
    #: "user" = token thường lấy ở Graph API Explorer
    #: "system" = token Người dùng hệ thống của Business Manager (vĩnh viễn)
    token_type: str = "user"


@router.post("")
async def add_account(req: AddAccountRequest):
    try:
        result = await facebook.add_account(
            req.name, req.access_token, req.app_id, req.app_secret, req.token_type)
        return {"status": "ok", "account": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_accounts():
    accounts = await facebook.get_accounts()
    return {"status": "ok", "accounts": accounts}


@router.delete("/{account_id}")
async def remove_account(account_id: int):
    await facebook.delete_account(account_id)
    return {"status": "ok"}


@router.post("/{account_id}/discover-pages")
async def discover_pages(account_id: int):
    try:
        result = await facebook.discover_pages_detailed(account_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    pages = result["pages"]
    out = {"status": "ok", "pages": pages, "count": len(pages),
           "steps": result["steps"]}

    # Quét xong mà rỗng là lúc người dùng cần lời giải thích nhất — trước đây chỉ
    # báo "Tìm thấy 0 Fanpage" rồi thôi, không ai biết phải sửa ở đâu.
    if not pages:
        accounts = await facebook.get_accounts()
        kind = next((a["token_type"] for a in accounts if a["id"] == account_id), "user")
        out["hint"] = facebook.explain_no_pages(result["steps"], kind)
    return out


class UpdateTokenRequest(BaseModel):
    access_token: str
    app_id: str = ""
    app_secret: str = ""
    #: Bỏ trống thì giữ nguyên kiểu token của tài khoản
    token_type: str | None = None


@router.put("/{account_id}/token")
async def update_token(account_id: int, req: UpdateTokenRequest):
    """Thay token cho tài khoản đã có và làm mới token của tất cả Page."""
    try:
        result = await facebook.update_account_token(
            account_id, req.access_token, req.app_id, req.app_secret, req.token_type
        )
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{account_id}/token-status")
async def token_status(account_id: int):
    """Kiểm tra token còn sống không, còn bao nhiêu ngày."""
    return {"status": "ok", **await facebook.check_account_token(account_id)}
