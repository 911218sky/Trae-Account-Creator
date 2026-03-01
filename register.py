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
import httpx

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
from src.storage import (
    save_session as storage_save_session,
    save_account as storage_save_account,
    save_account_data as storage_save_account_data,
    cookies_to_header as storage_cookies_to_header,
)  # noqa: E402

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


 


class TraeRegistrar:
    def __init__(self, settings: Settings, accounts_lock: asyncio.Lock) -> None:
        self.settings = settings
        self.accounts_lock = accounts_lock
        self._token_response_text: str | None = None
    
    async def _handle_response(self, response: Response) -> None:
        url = response.url
        
        if "trae.ai" in url:
            logger.debug(f"API call detected: {url}")
        
        token_endpoint_hit = (
            "GetUserToken" in url
            or "/cloudide/api/v3/common/GetUserToken" in url
            or url.startswith("https://api-sg-central.trae.ai/cloudide/api/v3/common/GetUserToken")
        )
        if token_endpoint_hit and not self._token_response_text:
            try:
                logger.info(f"GetUserToken API call observed: {url}")
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
        
        if "GetUserInfo" in url:
            logger.info(f"GetUserInfo API call observed: {url}")

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

    async def _open_page(self):
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
            try:
                yield page
            finally:
                await context.close()
                await browser.close()

    async def _ensure_token_captured(self, page: Page) -> None:
        logger.info("Waiting for GetUserToken and GetUserInfo API calls...")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)
        max_retries = 3
        retry_count = 0
        while not self._token_response_text and retry_count < max_retries:
            retry_count += 1
            logger.warning(f"Token not captured yet, refreshing page (attempt {retry_count}/{max_retries})...")
            try:
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

    @staticmethod
    def _fetch_user_info_sync(cookies_list: list[dict[str, Any]], token_value: str | None) -> dict[str, Any] | None:
        try:
            url = "https://ug-normal.trae.ai/cloudide/api/v3/trae/GetUserInfo"
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Cookie": storage_cookies_to_header(cookies_list),
            }
            if token_value:
                headers["Authorization"] = f"Bearer {token_value}"
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(url, json={"IfWebPage": True}, headers=headers)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        return data.get("Result") or data
                    except Exception as e:
                        logger.warning(f"Failed to parse direct user info JSON: {e}")
                else:
                    logger.warning(f"GetUserInfo POST returned status {resp.status_code}")
        except Exception as e:
            logger.warning(f"Failed direct GetUserInfo POST: {e}")
        return None

    async def run_one(self) -> None:
        logger.info("Starting single account registration process...")
        self._token_response_text = None

        async with AsyncMailClient() as mail_client:
            email = mail_client.get_email()
            if not email:
                raise RuntimeError("Failed to generate email. Please check CUSTOM_DOMAIN.")

            password = generate_password(self.settings.password_length)

            async for page in self._open_page():
                await self._sign_up(page, mail_client, email, password)
                await storage_save_account(self.settings.accounts_file, email, password, self.accounts_lock)
                logger.info("Account saved to: %s", self.settings.accounts_file)
                await self._ensure_token_captured(page)
                cookies = await page.context.cookies()
                token_value = extract_token(self._token_response_text)
                if token_value:
                    logger.info(f"✓ Token will be saved (length: {len(token_value)})")
                else:
                    logger.warning("✗ No token captured - session will be saved without token")
                cookies_list = [dict(c) for c in cookies]
                user_info = self._fetch_user_info_sync(cookies_list, token_value)
                if user_info is not None:
                    logger.info("✓ User info fetched via direct POST")
                session_path = self.settings.cookies_dir / f"{_safe_filename(email)}.json"
                await storage_save_session(session_path, token_value, cookies_list)
                logger.info("Session saved to: %s", session_path)
                await storage_save_account_data(
                    self.settings.accounts_dir,
                    email,
                    token_value,
                    cookies_list,
                    user_info=user_info,
                    plan_type="Free"
                )
                logger.info("Account data saved to: %s/%s.json", self.settings.accounts_dir, _safe_filename(email))
                await asyncio.sleep(2)


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
        
        # Determine command to run
        if getattr(sys, "frozen", False):
            # In frozen mode, call our internal command
            cmd = [sys.executable, "_install_browsers_internal", browser_name]
        else:
            # In dev mode, use standard playwright module
            cmd = [sys.executable, "-m", "playwright", "install", browser_name]
            
        if progress_cb:
            proc = subprocess.Popen(
                cmd,
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
            subprocess.run(cmd, check=True, env=env)
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
    
    if argv and argv[0].strip().lower() == "_install_browsers_internal":
        parser = argparse.ArgumentParser(prog=f"{Path(sys.argv[0]).name} _install_browsers_internal")
        parser.add_argument("browser", nargs="?", default="chromium")
        return "_install_browsers_internal", parser.parse_args(argv[1:])
    
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
    
    if mode == "_install_browsers_internal":
        from playwright.__main__ import main as pw_main
        sys.argv = [sys.argv[0], "install", args.browser]
        try:
            pw_main()
            return 0
        except SystemExit as e:
            return e.code
    
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
