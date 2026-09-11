"""Shared crawl4ai fetch helper: real headless-browser fetch with a couple of
retries and a check for common bot-block/CAPTCHA pages. A random delay is
left to callers between requests (see run_all.py) to look less scripted."""

import asyncio

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CacheMode, CrawlerRunConfig

BLOCK_SIGNALS = [
    "robot or human",
    "captcha",
    "are you a human",
    "access denied",
    "unusual traffic",
    "sorry, we just",
]

_BROWSER_CONFIG = BrowserConfig(headless=True, user_agent_mode="random")


def looks_blocked(html_or_markdown: str) -> bool:
    text = (html_or_markdown or "").lower()
    return any(signal in text for signal in BLOCK_SIGNALS)


async def fetch_html(
    url: str, wait_for_selector: str | None = None, retries: int = 2, magic: bool = True
) -> tuple[bool, str]:
    """Returns (ok, html). ok is False if every attempt failed or was blocked.

    Block-detection only scans the rendered page text (markdown), not the raw
    HTML — raw HTML routinely contains the word "captcha" in legitimate
    fraud-prevention scripts (e.g. reCAPTCHA's own <script> tag), which would
    otherwise falsely flag ordinary pages as blocked.

    wait_for_selector: a CSS selector (e.g. the product-card container) that
    crawl4ai should wait to appear before considering the page loaded. Some
    stores' product grids render asynchronously after the initial page load,
    so without this the page can be captured before any products show up —
    this happened intermittently on Best Buy during testing.

    magic: crawl4ai's bot-evasion mode (simulated scrolling/clicking). Needed
    on search-results pages to get past Amazon/Best Buy's detection, but it
    causes an unwanted navigation/crash on Amazon's *product* pages specfically
    (their interactive elements — image carousel, variant pickers — seem to
    trigger it). Pass magic=False for individual product-page fetches.
    """
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        magic=magic,
        simulate_user=magic,
        page_timeout=30000,
        wait_for=f"css:{wait_for_selector}" if wait_for_selector else None,
    )
    for attempt in range(1, retries + 1):
        # A fresh browser session per attempt — if attempt 1 got a degraded
        # or rate-limited response, retrying in the same session would likely
        # just repeat it.
        try:
            async with AsyncWebCrawler(config=_BROWSER_CONFIG) as crawler:
                result = await crawler.arun(url=url, config=run_config)
                html = result.html or ""
                if result.success and not looks_blocked(result.markdown or ""):
                    return True, html
        except Exception as e:
            # e.g. wait_for_selector never appeared (page had no results,
            # or rendered differently than expected) — treat as a failed
            # attempt, not a crash.
            print(f"  fetch error on attempt {attempt} for {url}: {e}")
        if attempt < retries:
            await asyncio.sleep(3 * attempt)
    return False, ""
