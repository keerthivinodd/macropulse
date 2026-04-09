"""
Best-effort browser-backed fetch helpers for challenge-heavy sources.

These helpers are optional at runtime:
- If Playwright is installed and can launch, we can fetch rendered HTML.
- If the environment blocks browser subprocesses or the site still serves a
  challenge page, callers simply fall back to plain HTTP behavior.
"""
from __future__ import annotations

import os


async def _open_page(url: str, wait_ms: int) -> tuple[str | None, list[str]]:
    from playwright.async_api import async_playwright

    browser_channel = os.getenv("BROWSER_CHANNEL") or None
    user_data_dir = os.getenv("BROWSER_USER_DATA_DIR", "").strip()
    headless = os.getenv("BROWSER_HEADLESS", "true").lower() in {"1", "true", "yes"}

    async with async_playwright() as playwright:
        if user_data_dir:
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                channel=browser_channel,
                headless=headless,
            )
            owns_context = True
        else:
            browser = await playwright.chromium.launch(
                headless=headless,
                channel=browser_channel,
            )
            context = await browser.new_context()
            owns_context = True

        try:
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=120000)
            await page.wait_for_timeout(wait_ms)
            content = await page.content()
            links: list[str] = await page.eval_on_selector_all(
                "a",
                "els => els.map(a => a.href).filter(Boolean)",
            )
            return content, links
        finally:
            if owns_context:
                await context.close()


async def fetch_page_content(url: str, wait_ms: int = 3000) -> str | None:
    if os.getenv("ENABLE_BROWSER_FETCH", "").lower() not in {"1", "true", "yes"}:
        return None
    try:
        content, _ = await _open_page(url, wait_ms)
        return content
    except Exception:
        return None


async def fetch_page_links(url: str, wait_ms: int = 3000) -> list[str]:
    if os.getenv("ENABLE_BROWSER_FETCH", "").lower() not in {"1", "true", "yes"}:
        return []
    try:
        _, links = await _open_page(url, wait_ms)
        return links
    except Exception:
        return []
