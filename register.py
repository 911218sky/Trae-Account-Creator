import sys
import os

# Fix for Playwright browser path in frozen executable
# 1. Check if there is a 'browsers' folder next to the executable (Portable Mode)
# 2. If not, use system default location (Install Mode)
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
    local_browsers_path = os.path.join(base_dir, 'browsers')
    
    if os.path.exists(local_browsers_path):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = local_browsers_path
        print(f"Using local browsers from: {local_browsers_path}")
    else:
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
        print("Using system default browsers")

import asyncio
import random
import string
import re
import json
from playwright.async_api import async_playwright
from mail_client import AsyncMailClient

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_DIR = os.path.join(BASE_DIR, "cookies")
ACCOUNTS_FILE = os.path.join(BASE_DIR, "accounts.txt")
os.makedirs(COOKIES_DIR, exist_ok=True)

# Configuration
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"

def generate_password(length=12):
    """Generate a strong random password."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=length))

async def save_account(email, password):
    """Save the created account details to a file."""
    write_header = not os.path.exists(ACCOUNTS_FILE) or os.path.getsize(ACCOUNTS_FILE) == 0
    with open(ACCOUNTS_FILE, "a", encoding="utf-8") as f:
        if write_header:
            f.write("Email    Password\n")
        f.write(f"{email}    {password}\n")
    print(f"Account saved to: {ACCOUNTS_FILE}")

async def run_registration():
    """Run the registration process for a single account."""
    print("Starting single account registration process...")
    
    mail_client = AsyncMailClient()
    browser = None
    context = None
    page = None

    try:
        # 1. Setup Mail
        await mail_client.start()
        email = mail_client.get_email()
        password = generate_password()

        # 2. Setup Browser
        async with async_playwright() as p:
            print(f"Launching browser (Headless: {HEADLESS})...")
            browser = await p.chromium.launch(
                headless=HEADLESS,
                args=[
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-software-rasterizer",
                    "--disable-extensions",
                ]
            )
            context = await browser.new_context()
            page = await context.new_page()

            # 3. Sign Up Process
            print("Navigating to sign-up page...")
            await page.goto("https://www.trae.ai/sign-up")
            
            # Fill Email
            print(f"Filling email: {email}")
            await page.get_by_role("textbox", name="Email").fill(email)
            await page.get_by_text("Send Code").click()
            print("Verification code sent, waiting for email...")

            # Poll for code
            verification_code = None
            for i in range(12): # 60 seconds max
                await mail_client.check_emails()
                if mail_client.last_verification_code:
                    verification_code = mail_client.last_verification_code
                    break
                print(f"Checking email... ({i+1}/12)")
                await asyncio.sleep(5)

            if not verification_code:
                print("Failed to receive verification code within 60 seconds.")
                return

            # Fill Code & Password
            print(f"Entering verification code: {verification_code}")
            await page.get_by_role("textbox", name="Verification code").fill(verification_code)
            await page.get_by_role("textbox", name="Password").fill(password)

            # Click Sign Up
            signup_btns = page.get_by_text("Sign Up")
            if await signup_btns.count() > 1:
                await signup_btns.nth(1).click()
            else:
                await signup_btns.click()
            
            print("Submitting registration...")

            # Verify Success (Check URL change or specific element)
            try:
                await page.wait_for_url(lambda url: "/sign-up" not in url, timeout=20000)
                print("Registration successful (page redirected)")
            except:
                # Check for errors
                if await page.locator(".error-message").count() > 0:
                    err = await page.locator(".error-message").first.inner_text()
                    print(f"Registration failed: {err}")
                    return
                print("Registration success check timed out, continuing anyway...")

            # Save Account
            await save_account(email, password)

            # 4. Claim Gift
            print("Checking for anniversary gift...")
            try:
                await page.goto("https://www.trae.ai/2026-anniversary-gift")
                await page.wait_for_load_state("networkidle")

                claim_btn = page.get_by_role("button", name=re.compile("claim", re.IGNORECASE))
                if await claim_btn.count() > 0:
                    text = await claim_btn.first.inner_text()
                    if "claimed" in text.lower():
                        print("Gift status: Already claimed")
                    else:
                        print(f"Clicking claim button: {text}")
                        await claim_btn.first.click()
                        # Wait for status update
                        try:
                            await page.wait_for_function(
                                "btn => btn.innerText.toLowerCase().includes('claimed')",
                                arg=await claim_btn.first.element_handle(),
                                timeout=10000
                            )
                            print("Gift claimed successfully!")
                        except:
                            print("Clicked claim, but status didn't update to 'Claimed'.")
                else:
                    print("Claim button not found.")
            except Exception as e:
                print(f"Error checking gift: {e}")

            # 5. Save Cookies
            cookies = await context.cookies()
            cookie_path = os.path.join(COOKIES_DIR, f"{email}.json")
            with open(cookie_path, "w", encoding="utf-8") as f:
                json.dump(cookies, f)
            print(f"Browser cookies saved to: {cookie_path}")
            
            # Wait a bit before closing to ensure everything settles
            await asyncio.sleep(2)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if mail_client:
            await mail_client.close()
        # Browser closes automatically with context manager

async def run_batch(total, concurrency):
    """Run batch registration with specified concurrency."""
    if total <= 0:
        print("Batch size must be greater than 0.")
        return
    if concurrency <= 0:
        print("Concurrency must be greater than 0.")
        return
    concurrency = min(concurrency, total)
    print(f"Starting batch registration. Total: {total}, Concurrency: {concurrency}")

    queue = asyncio.Queue()
    for i in range(1, total + 1):
        queue.put_nowait(i)
    for _ in range(concurrency):
        queue.put_nowait(None)

    async def worker(worker_id):
        while True:
            index = await queue.get()
            if index is None:
                queue.task_done()
                return
            print(f"[Worker {worker_id}] Starting account {index}/{total}...")
            try:
                await run_registration()
            finally:
                print(f"[Worker {worker_id}] Finished account {index}/{total}.")
                queue.task_done()

    tasks = [asyncio.create_task(worker(i + 1)) for i in range(concurrency)]
    await queue.join()
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "install-browsers":
        print("Installing Playwright browsers...")
        import subprocess
        try:
            # We need to install the browser binary
            # This is tricky in a frozen environment because 'playwright' module path is different
            # But we can try to use the python -m playwright install command if python is available
            # Or use the internal playwright driver if we can access it
            
            # Simple fallback: Try to run `playwright install chromium` assuming it's in path or accessible
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
            print("Browsers installed successfully.")
        except Exception as e:
            print(f"Failed to install browsers: {e}")
            print("Please try running: 'uv run playwright install chromium' or 'pip install playwright && playwright install chromium'")
        sys.exit(0)

    total = 1
    concurrency = 1
    if len(sys.argv) > 1:
        try:
            total = int(sys.argv[1])
        except ValueError:
            print("Error: Please provide total number of accounts (integer).")
            sys.exit(1)
    if len(sys.argv) > 2:
        try:
            concurrency = int(sys.argv[2])
        except ValueError:
            print("Error: Please provide concurrency level (integer).")
            sys.exit(1)
    
    try:
        asyncio.run(run_batch(total, concurrency))
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
