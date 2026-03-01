import asyncio
import json
from pathlib import Path
from typing import Any

def cookies_to_header(cookies: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for c in cookies:
        name = c.get("name")
        value = c.get("value")
        if not isinstance(name, str) or not isinstance(value, str):
            continue
        parts.append(f"{name}={value}")
    return "; ".join(parts)

def _write_session_sync(session_path: Path, token_value: str | None, cookies: list[dict[str, Any]]) -> None:
    session_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "token": token_value or "",
        "cookie": cookies_to_header(cookies),
    }
    with session_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

async def save_session(session_path: Path, token_value: str | None, cookies: list[dict[str, Any]]) -> None:
    await asyncio.to_thread(_write_session_sync, session_path, token_value, cookies)

def _append_account_sync(accounts_file: Path, email: str, password: str) -> None:
    write_header = not accounts_file.exists() or accounts_file.stat().st_size == 0
    with accounts_file.open("a", encoding="utf-8") as f:
        if write_header:
            f.write("Email    Password\n")
        f.write(f"{email}    {password}\n")

async def save_account(accounts_file: Path, email: str, password: str, lock: asyncio.Lock) -> None:
    async with lock:
        await asyncio.to_thread(_append_account_sync, accounts_file, email, password)

def _write_account_data_sync(
    accounts_dir: Path,
    email: str,
    token_value: str | None,
    cookies: list[dict[str, Any]],
    user_info: dict[str, Any] | None = None,
    plan_type: str = "Free"
) -> None:
    import uuid
    accounts_dir.mkdir(parents=True, exist_ok=True)
    safe_email = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in email).strip("._") or "account"
    account_file = accounts_dir / f"{safe_email}.json"
    account_id = str(uuid.uuid4())
    if user_info and user_info.get("ScreenName"):
        username = user_info["ScreenName"]
    else:
        username = email.split("@")[0] if "@" in email else email
    avatar_url = ""
    user_id = ""
    tenant_id = ""
    region = ""
    if user_info:
        avatar_url = user_info.get("AvatarUrl", "")
        user_id = user_info.get("UserID", "")
        tenant_id = user_info.get("TenantID", "")
        region = user_info.get("Region", "")
    account_entry = {
        "avatar_url": avatar_url,
        "cookies": cookies_to_header(cookies),
        "email": email,
        "jwt_token": token_value or "",
        "machine_id": account_id,
        "name": username,
        "plan_type": plan_type,
        "region": region,
        "tenant_id": tenant_id,
        "user_id": user_id
    }
    with account_file.open("w", encoding="utf-8") as f:
        json.dump([account_entry], f, ensure_ascii=False, indent=2)

async def save_account_data(
    accounts_dir: Path,
    email: str,
    token_value: str | None,
    cookies: list[dict[str, Any]],
    user_info: dict[str, Any] | None = None,
    plan_type: str = "Free"
) -> None:
    await asyncio.to_thread(_write_account_data_sync, accounts_dir, email, token_value, cookies, user_info, plan_type)

