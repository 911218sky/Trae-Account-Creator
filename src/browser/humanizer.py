from __future__ import annotations
import asyncio
import random
import string
from typing import Any
from playwright.async_api import Page

class Humanizer:
    async def type_text(
        self,
        page: Page,
        locator: Any,
        text: str,
        min_delay_ms: int = 40,
        max_delay_ms: int = 120,
        typo_chance: float = 0.03,
    ) -> None:
        await locator.click()
        for ch in text:
            if random.random() < typo_chance:
                wrong = random.choice(string.ascii_letters + string.digits)
                await page.keyboard.type(wrong, delay=random.randint(min_delay_ms, max_delay_ms))
                await page.keyboard.press("Backspace")
            await page.keyboard.type(ch, delay=random.randint(min_delay_ms, max_delay_ms))
            await asyncio.sleep(random.uniform(0.02, 0.10))
    
    async def human_click(self, page: Page, locator: Any) -> None:
        try:
            box = await locator.bounding_box()
            if box is None:
                await locator.scroll_into_view_if_needed()
                box = await locator.bounding_box()
            if box is None:
                await locator.click()
                return
            target_x = box["x"] + box["width"] / 2 + random.uniform(-3, 3)
            target_y = box["y"] + box["height"] / 2 + random.uniform(-3, 3)
            steps = random.randint(5, 12)
            start_x = target_x + random.uniform(-100, 100)
            start_y = target_y + random.uniform(-100, 100)
            await page.mouse.move(start_x, start_y, steps=steps)
            await asyncio.sleep(random.uniform(0.05, 0.15))
            await page.mouse.move(target_x, target_y, steps=steps)
            await asyncio.sleep(random.uniform(0.03, 0.10))
            await page.mouse.click(target_x, target_y, delay=random.randint(30, 120))
        except Exception:
            await locator.click()
    
    async def random_scroll(self, page: Page) -> None:
        try:
            dx = 0
            dy = random.randint(200, 600)
            await page.mouse.wheel(dx, dy)
            await asyncio.sleep(random.uniform(0.05, 0.20))
        except Exception:
            await page.evaluate("window.scrollBy(0, Math.floor(200 + Math.random()*400))")
