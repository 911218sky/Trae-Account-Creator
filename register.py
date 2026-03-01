from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import secrets
import string
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from dotenv import load_dotenv

load_dotenv()

ansi_re = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
ctrl_re = re.compile(r"[\x00-\x1F\x7F]")

def _sanitize_output(s: str) -> str:
    s = ansi_re.sub("", s)
    s = s.replace("\r", " ").replace("\b", " ")
    s = ctrl_re.sub(" ", s)
    return " ".join(s.split())


def _configure_playwright_browsers_path() -> None:
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    local_browsers_path = os.path.join(base_dir, "browsers")
    if os.path.exists(local_browsers_path):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = local_browsers_path
        print(f"Using local browsers from: {local_browsers_path}")
    else:
        if getattr(sys, "frozen", False):
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
            print("Using system default browsers")


_configure_playwright_browsers_path()

from playwright.async_api import Page, Response, async_playwright  # noqa: E402
from src.mail_client import AsyncMailClient  # noqa: E402
from src.config import env_bool, env_int  # noqa: E402
from src.logger import setup_logger  # noqa: E402

logger = setup_logger("register")

JWT_RE = re.compile(r"eyJ[\w-]+\.[\w-]+\.[\w-]+")


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    cookies_dir: Path
    accounts_dir: Path
    accounts_file: Path
    headless: bool
    password_length: int
    email_wait_timeout_s: int
    email_poll_interval_s: int
    navigation_timeout_ms: int
    signup_url: str
    gift_url: str

    @staticmethod
    def load() -> Settings:
        # Use executable directory for frozen app, script directory otherwise
        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).resolve().parent
        else:
            base_dir = Path(__file__).resolve().parent
        
        cookies_dir = base_dir / "cookies"
        cookies_dir.mkdir(parents=True, exist_ok=True)
        
        accounts_dir = base_dir / "accounts"
        accounts_dir.mkdir(parents=True, exist_ok=True)
        
        return Settings(
            base_dir=base_dir,
            cookies_dir=cookies_dir,
            accounts_dir=accounts_dir,
            accounts_file=base_dir / "accounts.txt",
            headless=env_bool("HEADLESS", False),
            password_length=max(8, env_int("PASSWORD_LENGTH", 12)),
            email_wait_timeout_s=max(10, env_int("EMAIL_WAIT_TIMEOUT_S", 60)),
            email_poll_interval_s=max(1, env_int("EMAIL_POLL_INTERVAL_S", 5)),
            navigation_timeout_ms=max(1_000, env_int("NAVIGATION_TIMEOUT_MS", 20_000)),
            signup_url=os.getenv("SIGNUP_URL", "https://www.trae.ai/sign-up").strip(),
            gift_url=os.getenv("GIFT_URL", "https://www.trae.ai/2026-anniversary-gift").strip(),
        )


def generate_password(length: int) -> str:
    letters = string.ascii_letters
    digits = string.digits
    symbols = "!@#$%^&*"
    if length < 8:
        length = 8

    required = [
        secrets.choice(letters),
        secrets.choice(digits),
        secrets.choice(symbols),
    ]
    remaining = length - len(required)
    pool = letters + digits + symbols
    password_chars = required + [secrets.choice(pool) for _ in range(remaining)]
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


def _safe_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._") or "account"


def extract_token(token_response_text: str | None) -> str | None:
    if not token_response_text:
        return None
    try:
        obj = json.loads(token_response_text)
        token = obj.get("Result", {}).get("Token")
        if isinstance(token, str) and token.strip():
            return token.strip()
    except Exception:
        pass
    
    match = JWT_RE.search(token_response_text)
    return match.group(0) if match else None


def _append_account_sync(accounts_file: Path, email: str, password: str) -> None:
    write_header = not accounts_file.exists() or accounts_file.stat().st_size == 0
    with accounts_file.open("a", encoding="utf-8") as f:
        if write_header:
            f.write("Email    Password\n")
        f.write(f"{email}    {password}\n")


async def save_account(accounts_file: Path, email: str, password: str, lock: asyncio.Lock) -> None:
    async with lock:
        await asyncio.to_thread(_append_account_sync, accounts_file, email, password)
    logger.info("Account saved to: %s", accounts_file)


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
        "token": token_value,
        "cookie": cookies_to_header(cookies),
    }
    with session_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


async def save_session(session_path: Path, token_value: str | None, cookies: list[dict[str, Any]]) -> None:
    await asyncio.to_thread(_write_session_sync, session_path, token_value, cookies)
    logger.info("Session saved to: %s", session_path)


def _write_account_data_sync(
    accounts_dir: Path,
    email: str,
    token_value: str | None,
    cookies: list[dict[str, Any]],
    user_info: dict[str, Any] | None = None,
    plan_type: str = "Free"
) -> None:
    """Save account data as individual JSON file in array format"""
    import uuid
    
    accounts_dir.mkdir(parents=True, exist_ok=True)
    
    # Use email as filename (sanitized)
    safe_email = _safe_filename(email)
    account_file = accounts_dir / f"{safe_email}.json"
    
    # Generate account ID
    account_id = str(uuid.uuid4())
    
    # Extract username from email or user_info
    if user_info and user_info.get("ScreenName"):
        username = user_info["ScreenName"]
    else:
        username = email.split("@")[0] if "@" in email else email
    
    # Extract user info from API response
    avatar_url = ""
    user_id = ""
    tenant_id = ""
    region = ""
    
    if user_info:
        avatar_url = user_info.get("AvatarUrl", "")
        user_id = user_info.get("UserID", "")
        tenant_id = user_info.get("TenantID", "")
        region = user_info.get("Region", "")
    
    # Create account entry
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
    
    # Save as array with single item
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
    """Save account data as individual file"""
    await asyncio.to_thread(_write_account_data_sync, accounts_dir, email, token_value, cookies, user_info, plan_type)
    safe_email = _safe_filename(email)
    logger.info("Account data saved to: %s/%s.json", accounts_dir, safe_email)


class TraeRegistrar:
    def __init__(self, settings: Settings, accounts_lock: asyncio.Lock) -> None:
        self.settings = settings
        self.accounts_lock = accounts_lock
        self._token_response_text: str | None = None
        self._user_info_response_text: str | None = None

    async def _handle_response(self, response: Response) -> None:
        url = response.url
        
        if "trae.ai" in url:
            logger.debug(f"API call detected: {url}")
        
        if "GetUserToken" in url and not self._token_response_text:
            try:
                self._token_response_text = await response.text()
                logger.info(f"✓ Captured GetUserToken response from: {url}")
                token = extract_token(self._token_response_text)
                if token:
                    logger.info(f"✓ Successfully extracted token (length: {len(token)})")
                else:
                    logger.warning("✗ GetUserToken response captured but token extraction failed")
                    logger.debug(f"Response content: {self._token_response_text[:500]}...")
            except Exception as e:
                logger.error(f"Failed to read token response: {e}", exc_info=True)
        
        if "GetUserInfo" in url and not self._user_info_response_text:
            try:
                self._user_info_response_text = await response.text()
                logger.info(f"✓ Captured GetUserInfo response from: {url}")
                try:
                    data = json.loads(self._user_info_response_text)
                    result = data.get("Result", {})
                    screen_name = result.get("ScreenName", "Unknown")
                    logger.info(f"✓ User info: {screen_name}")
                except Exception:
                    logger.debug("Could not parse GetUserInfo response")
            except Exception as e:
                logger.error(f"Failed to read user info response: {e}", exc_info=True)
        url = response.url
        
        if "trae.ai" in url:
            logger.debug(f"API call detected: {url}")
        
        if "GetUserToken" in url and not self._token_response_text:
            try:
                self._token_response_text = await response.text()
                logger.info(f"✓ Captured GetUserToken response from: {url}")
                token = extract_token(self._token_response_text)
                if token:
                    logger.info(f"✓ Successfully extracted token (length: {len(token)})")
                else:
                    logger.warning("✗ GetUserToken response captured but token extraction failed")
                    logger.debug(f"Response content: {self._token_response_text[:500]}...")
            except Exception as e:
                logger.error(f"Failed to read token response: {e}", exc_info=True)

    @staticmethod
    async def _wait_for_verification_code(
        mail_client: AsyncMailClient,
        *,
        timeout_s: int,
        poll_interval_s: int,
    ) -> str | None:
        deadline = asyncio.get_running_loop().time() + timeout_s
        attempt = 0
        while asyncio.get_running_loop().time() < deadline:
            attempt += 1
            await mail_client.check_emails()
            if mail_client.last_verification_code:
                return mail_client.last_verification_code
            logger.info("Checking email... (attempt %d)", attempt)
            await asyncio.sleep(poll_interval_s)
        return None

    async def _claim_gift(self, page: Page) -> None:
        logger.info("Checking for anniversary gift...")
        try:
            await page.goto(self.settings.gift_url)
            await page.wait_for_load_state("networkidle")

            claim_btn = page.get_by_role("button", name=re.compile("claim", re.IGNORECASE))
            if await claim_btn.count() <= 0:
                logger.info("Claim button not found.")
                return

            btn_text = (await claim_btn.first.inner_text()).strip()
            if "claimed" in btn_text.lower():
                logger.info("Gift status: Already claimed")
                return

            logger.info("Clicking claim button: %s", btn_text)
            await claim_btn.first.click()
            try:
                await page.wait_for_function(
                    "btn => btn && btn.innerText && btn.innerText.toLowerCase().includes('claimed')",
                    arg=await claim_btn.first.element_handle(),
                    timeout=10_000,
                )
                logger.info("Gift claimed successfully!")
            except Exception:
                logger.warning("Clicked claim, but status didn't update to 'Claimed'.")
        except Exception as e:
            logger.warning("Error checking gift: %s", e)

    async def _sign_up(self, page: Page, mail_client: AsyncMailClient, email: str, password: str) -> None:
        logger.info("Navigating to sign-up page...")
        await page.goto(self.settings.signup_url)
        await page.wait_for_load_state("networkidle")

        logger.info("Filling email: %s", email)
        email_input = page.get_by_role("textbox", name="Email")
        await email_input.wait_for(state="visible", timeout=10_000)
        await email_input.fill(email)
        
        logger.info("Clicking send code button...")
        send_code_btn = page.get_by_text("Send Code")
        await send_code_btn.click()
        logger.info("Verification code sent, waiting for email...")

        verification_code = await self._wait_for_verification_code(
            mail_client,
            timeout_s=self.settings.email_wait_timeout_s,
            poll_interval_s=self.settings.email_poll_interval_s,
        )
        if not verification_code:
            raise RuntimeError(
                f"Failed to receive verification code within {self.settings.email_wait_timeout_s} seconds."
            )

        logger.info("Entering verification code")
        code_input = page.get_by_role("textbox", name="Verification code")
        await code_input.wait_for(state="visible", timeout=10_000)
        await code_input.fill(verification_code)
        
        logger.info("Entering password")
        password_input = page.get_by_role("textbox", name="Password")
        await password_input.wait_for(state="visible", timeout=10_000)
        await password_input.fill(password)

        logger.info("Submitting registration...")
        signup_btns = page.get_by_text("Sign Up")
        btn_count = await signup_btns.count()
        
        if btn_count > 1:
            await signup_btns.nth(1).click()
        elif btn_count == 1:
            await signup_btns.click()
        else:
            await page.screenshot(path="debug_no_signup_btn.png")
            raise RuntimeError("Could not find 'Sign Up' button")
        
        try:
            await page.wait_for_url(
                lambda url: "/sign-up" not in url, timeout=self.settings.navigation_timeout_ms
            )
            logger.info("Registration successful (page redirected)")
        except Exception:
            err_locator = page.locator(".error-message").first
            if await err_locator.count() > 0:
                err = (await err_locator.inner_text()).strip()
                raise RuntimeError(f"Registration failed: {err}") from None
            
            current_url = page.url
            if "/sign-up" in current_url:
                logger.warning("Still on sign-up page after timeout - button click may have failed")
                await page.screenshot(path="debug_after_submit.png")
            else:
                logger.info("Registration appears successful (not on sign-up page)")

    async def run_one(self) -> None:
        logger.info("Starting single account registration process...")
        self._token_response_text = None

        async with AsyncMailClient() as mail_client:
            email = mail_client.get_email()
            if not email:
                raise RuntimeError("Failed to generate email. Please check CUSTOM_DOMAIN.")

            password = generate_password(self.settings.password_length)

            async with async_playwright() as p:
                logger.info("Launching browser (Headless: %s)...", self.settings.headless)
                browser = await p.chromium.launch(
                    headless=self.settings.headless,
                    args=[
                        "--disable-gpu",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-software-rasterizer",
                        "--disable-extensions",
                    ],
                )
                context = await browser.new_context()
                page = await context.new_page()
                page.on("response", self._handle_response)

                await self._sign_up(page, mail_client, email, password)
                await save_account(self.settings.accounts_file, email, password, self.accounts_lock)
                
                logger.info("Waiting for GetUserToken and GetUserInfo API calls...")
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
                
                # Retry logic: refresh page up to 3 times if token not captured
                max_retries = 3
                retry_count = 0
                
                while not self._token_response_text and retry_count < max_retries:
                    retry_count += 1
                    logger.warning(f"Token not captured yet, refreshing page (attempt {retry_count}/{max_retries})...")
                    try:
                        # Re-register the response handler to ensure it's active after refresh
                        page.remove_listener("response", self._handle_response)
                        page.on("response", self._handle_response)
                        
                        await page.reload()
                        await page.wait_for_load_state("networkidle")
                        await asyncio.sleep(3)
                        
                        if self._token_response_text:
                            logger.info(f"✓ Token captured after refresh (attempt {retry_count})")
                            break
                    except Exception as e:
                        logger.warning(f"Failed to refresh page (attempt {retry_count}): {e}")
                
                if not self._token_response_text:
                    logger.error("✗ Failed to capture token after all retries")
                    raise RuntimeError("JWT token is required but could not be captured after multiple attempts")
                
                await self._claim_gift(page)

                cookies = await context.cookies()
                token_value = extract_token(self._token_response_text)
                
                if token_value:
                    logger.info(f"✓ Token will be saved (length: {len(token_value)})")
                else:
                    logger.warning("✗ No token captured - session will be saved without token")
                
                cookies_list = [dict(c) for c in cookies]
                
                # Parse user info from captured response
                user_info = None
                if self._user_info_response_text:
                    try:
                        data = json.loads(self._user_info_response_text)
                        user_info = data.get("Result", {})
                        logger.info("✓ User info parsed successfully")
                    except Exception as e:
                        logger.warning(f"Failed to parse user info: {e}")
                
                # Save in old format (cookies folder)
                session_path = self.settings.cookies_dir / f"{_safe_filename(email)}.json"
                await save_session(session_path, token_value, cookies_list)
                
                # Save in new format (accounts folder) with user info
                await save_account_data(
                    self.settings.accounts_dir,
                    email,
                    token_value,
                    cookies_list,
                    user_info=user_info,
                    plan_type="Free"
                )

                await asyncio.sleep(2)

                await context.close()
                await browser.close()


async def run_batch(total: int, concurrency: int, settings: Settings, progress_cb: Optional[Callable[[int, int], None]] = None) -> None:
    if total <= 0:
        raise ValueError("Batch size must be greater than 0.")
    if concurrency <= 0:
        raise ValueError("Concurrency must be greater than 0.")

    concurrency = min(concurrency, total)
    logger.info("Starting batch registration. Total: %d, Concurrency: %d", total, concurrency)

    accounts_lock = asyncio.Lock()
    queue: asyncio.Queue[int | None] = asyncio.Queue()
    for i in range(1, total + 1):
        queue.put_nowait(i)
    for _ in range(concurrency):
        queue.put_nowait(None)

    completed = 0
    progress_lock = asyncio.Lock()

    async def worker(worker_id: int) -> None:
        nonlocal completed
        while True:
            index = await queue.get()
            try:
                if index is None:
                    return
                logger.info("[Worker %d] Starting account %d/%d...", worker_id, index, total)
                registrar = TraeRegistrar(settings, accounts_lock)
                await registrar.run_one()
                logger.info("[Worker %d] Finished account %d/%d.", worker_id, index, total)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("[Worker %d] Account %s failed.", worker_id, index)
            finally:
                queue.task_done()
                if index is not None:
                    async with progress_lock:
                        completed += 1
                        if progress_cb:
                            try:
                                progress_cb(completed, total)
                            except Exception:
                                pass

    tasks = [asyncio.create_task(worker(i + 1)) for i in range(concurrency)]
    await queue.join()
    await asyncio.gather(*tasks)
    if progress_cb:
        try:
            progress_cb(total, total)
        except Exception:
            pass


def install_playwright_browsers(browser_name: str, progress_cb: Optional[Callable[[int], None]] = None) -> int:
    logger.info("Installing Playwright browsers (%s)...", browser_name)
    try:
        base_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
        local_browsers_path = os.path.join(base_dir, "browsers")
        os.makedirs(local_browsers_path, exist_ok=True)
        env = os.environ.copy()
        env["PLAYWRIGHT_BROWSERS_PATH"] = local_browsers_path
        if progress_cb:
            proc = subprocess.Popen(
                [sys.executable, "-m", "playwright", "install", browser_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )
            percent = 0
            pct_re = re.compile(r"(\d{1,3})%")
            assert proc.stdout is not None
            for line in proc.stdout:
                raw = line.rstrip("\n")
                m = pct_re.search(raw)
                if m:
                    try:
                        percent = int(m.group(1))
                        progress_cb(max(0, min(100, percent)))
                    except Exception:
                        pass
                size_m = re.search(r"of\s+([\d\.]+\s+[KMG]iB)", raw)
                if m:
                    if size_m:
                        logger.info(f"Installing browsers: {percent}% of {size_m.group(1)}")
                    else:
                        logger.info(f"Installing browsers: {percent}%")
                else:
                    clean = _sanitize_output(raw)
                    if clean:
                        logger.info(clean)
            ret = proc.wait()
            if ret != 0:
                raise RuntimeError(f"Playwright install exited with code {ret}")
        else:
            subprocess.run([sys.executable, "-m", "playwright", "install", browser_name], check=True, env=env)
        logger.info("Browsers installed successfully.")
        return 0
    except Exception as e:
        logger.error("Failed to install browsers: %s", e)
        logger.error("Try: uv run playwright install %s", browser_name)
        return 1


def merge_accounts_command(accounts_dir: Path, output_file: Path) -> int:
    """Merge all account JSON files into a single list"""
    try:
        if not accounts_dir.exists():
            logger.error(f"Directory '{accounts_dir}' not found")
            return 1
        
        all_accounts = []
        json_files = list(accounts_dir.glob("*.json"))
        
        if not json_files:
            logger.warning(f"No JSON files found in '{accounts_dir}'")
            return 0
        
        logger.info(f"Found {len(json_files)} account file(s)")
        
        for json_file in sorted(json_files):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Handle both list and single object formats
                    if isinstance(data, list):
                        all_accounts.extend(data)
                        logger.info(f"  ✓ {json_file.name}: {len(data)} account(s)")
                    elif isinstance(data, dict):
                        all_accounts.append(data)
                        logger.info(f"  ✓ {json_file.name}: 1 account")
                    else:
                        logger.warning(f"  ⚠️  {json_file.name}: Unexpected format, skipped")
                        
            except json.JSONDecodeError as e:
                logger.error(f"  ✗ {json_file.name}: Invalid JSON - {e}")
            except Exception as e:
                logger.error(f"  ✗ {json_file.name}: Error - {e}")
        
        # Write merged accounts to output file
        if all_accounts:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_accounts, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Merged {len(all_accounts)} account(s) → {output_file}")
            return 0
        else:
            logger.warning("No accounts to merge")
            return 0
            
    except Exception as e:
        logger.error(f"Failed to merge accounts: {e}")
        return 1


def _parse_args(argv: list[str]) -> tuple[str, argparse.Namespace]:
    if argv and argv[0].strip().lower() == "install-browsers":
        parser = argparse.ArgumentParser(prog=f"{Path(sys.argv[0]).name} install-browsers")
        parser.add_argument("browser", nargs="?", default="chromium")
        return "install-browsers", parser.parse_args(argv[1:])
    
    if argv and argv[0].strip().lower() == "merge-accounts":
        from datetime import datetime
        default_output = f"accounts_merged-{datetime.now().strftime('%Y-%m-%d')}.json"
        parser = argparse.ArgumentParser(prog=f"{Path(sys.argv[0]).name} merge-accounts")
        parser.add_argument("--output", default=default_output, help="Output file path")
        return "merge-accounts", parser.parse_args(argv[1:])

    parser = argparse.ArgumentParser(prog=Path(sys.argv[0]).name)
    parser.add_argument("total", nargs="?", type=int, default=1)
    parser.add_argument("concurrency", nargs="?", type=int, default=1)
    return "run", parser.parse_args(argv)


def main(argv: list[str]) -> int:
    mode, args = _parse_args(argv)
    
    if mode == "install-browsers":
        return install_playwright_browsers(args.browser)
    
    if mode == "merge-accounts":
        settings = Settings.load()
        output_path = settings.base_dir / args.output
        return merge_accounts_command(settings.accounts_dir, output_path)

    settings = Settings.load()
    try:
        asyncio.run(run_batch(args.total, args.concurrency, settings))
        return 0
    except KeyboardInterrupt:
        logger.info("Process interrupted by user.")
        return 130
    except Exception as e:
        logger.error("%s", e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
