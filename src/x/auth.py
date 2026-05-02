from __future__ import annotations

from typing import TYPE_CHECKING

from src.x.exceptions import CrawlerAuthError

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext


LOGIN_URL = "https://x.com/login"
LOGIN_TIMEOUT_MS = 30_000


async def login(username: str, password: str) -> "BrowserContext":
    try:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise CrawlerAuthError("Playwright is required for X authentication") from exc

    playwright = await async_playwright().start()
    browser = None

    try:
        browser = await playwright.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()

        page.set_default_timeout(LOGIN_TIMEOUT_MS)
        await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=LOGIN_TIMEOUT_MS)

        username_input = page.locator('input[autocomplete="username"], input[name="text"]').first
        await username_input.fill(username)
        await page.get_by_role("button", name="Next").click()

        password_input = page.locator('input[name="password"], input[type="password"]').first
        await password_input.fill(password)
        await page.get_by_role("button", name="Log in").click()

        await page.wait_for_url(lambda url: "/login" not in url, timeout=LOGIN_TIMEOUT_MS)
        setattr(context, "_x_crawler_browser", browser)
        setattr(context, "_x_crawler_playwright", playwright)
        return context
    except PlaywrightTimeoutError as exc:
        if browser is not None:
            await browser.close()
        await playwright.stop()
        raise CrawlerAuthError("X login timed out") from exc
    except Exception as exc:
        if browser is not None:
            await browser.close()
        await playwright.stop()
        if isinstance(exc, CrawlerAuthError):
            raise
        raise CrawlerAuthError("X login failed") from exc
