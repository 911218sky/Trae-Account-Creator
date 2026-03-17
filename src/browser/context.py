from __future__ import annotations
import os
import random
from playwright.async_api import Browser

async def create_stealth_context(browser: Browser):
    ua_list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    ]
    ua = random.choice(ua_list)
    viewports = [(1920, 1080), (1366, 768), (1536, 864), (1440, 900)]
    vw, vh = random.choice(viewports)
    locale = os.getenv("BROWSER_LOCALE", "zh-TW")
    tz = os.getenv("BROWSER_TIMEZONE", "Asia/Taipei")
    color_scheme = random.choice(["dark", "light"])
    lat, lon = (25.033, 121.565)
    context = await browser.new_context(
        user_agent=ua,
        locale=locale,
        timezone_id=tz,
        viewport={"width": vw, "height": vh},
        color_scheme=color_scheme,
        geolocation={"latitude": lat, "longitude": lon},
        extra_http_headers={
            "Accept-Language": f"{locale},{locale.split('-')[0]};q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )
    await context.grant_permissions(["geolocation"])
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
        Object.defineProperty(navigator, 'languages', { get: () => ['zh-TW','zh','en-US','en'] });
        Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
        window.chrome = window.chrome || { runtime: {} };
    """)
    return context
