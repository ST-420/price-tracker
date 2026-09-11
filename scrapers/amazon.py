"""Discovers and price-checks phones/laptops on Amazon.

For each search term in queries.py, fetches one search-results page (which
already carries title + price + link for ~20-60 products at once — far
cheaper than visiting every product page individually), extracts each
product tile, matches it to an existing product or creates a new one, and
records its price. Logs and skips anything that fails instead of crashing
the whole run.
"""

import asyncio
import random
import re

from bs4 import BeautifulSoup

from . import db
from .fetch import fetch_html
from .queries import CATALOG_CAP, SEARCH_QUERIES

STORE = "amazon"
BASE_URL = "https://www.amazon.com"


SKIP_TITLE_WORDS = ("renewed", "refurbished", "used", "open box", "pre-owned")


def extract_products(html: str) -> list[dict]:
    """Returns genuine (non-sponsored, non-refurbished) organic results, best
    match first. Callers should generally just take items[0] — one canonical
    listing per search term, not every color/storage variant on the page."""
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select('div[data-component-type="s-search-result"]'):
        if "AdHolder" in (card.get("class") or []):
            continue  # sponsored placement — abbreviated markup, unreliable title

        # Cards can have two <h2>s: a short brand label (class "a-size-mini")
        # and the real title (class includes "a-text-normal"). Target the
        # latter specifically, else a search like "macbook air" yields "Apple".
        h2 = card.select_one("h2.a-text-normal") or card.select_one("h2")
        link = card.select_one('a.a-link-normal[href*="/dp/"]')
        price_el = card.select_one("span.a-price span.a-offscreen")
        if not (h2 and link and price_el):
            continue

        title = h2.get("aria-label") or h2.get_text(strip=True)
        price_text = price_el.get_text(strip=True)
        price_match = re.search(r"[\d,]+\.\d{2}", price_text)
        if not title or not price_match:
            continue
        if any(word in title.lower() for word in SKIP_TITLE_WORDS):
            continue

        href = link["href"]
        url = href if href.startswith("http") else BASE_URL + href
        items.append({
            "title": title.strip(),
            "price": float(price_match.group(0).replace(",", "")),
            "url": url.split("?")[0],
        })
    return items


async def run():
    conn = db.connect()
    found, saved, failed = 0, 0, 0
    try:
        with conn.cursor() as cur:
            for category, terms in SEARCH_QUERIES.items():
                for term in terms:
                    if db.catalog_size(cur) >= CATALOG_CAP:
                        print(f"[{STORE}] catalog cap ({CATALOG_CAP}) reached, stopping discovery")
                        break

                    url = f"{BASE_URL}/s?k={term.replace(' ', '+')}"
                    ok, html = await fetch_html(url, wait_for_selector='div[data-component-type="s-search-result"]')
                    if not ok:
                        print(f"[{STORE}] FAILED (blocked or error): {term}")
                        failed += 1
                        await asyncio.sleep(random.uniform(3, 6))
                        continue

                    items = extract_products(html)
                    print(f"[{STORE}] {term}: {len(items)} candidates found")
                    if not items:
                        await asyncio.sleep(random.uniform(3, 6))
                        continue
                    found += 1

                    item = items[0]  # best organic match for this search term
                    try:
                        product_id = db.find_or_create_product(cur, term, category, item["title"])
                        db.upsert_listing_price(cur, product_id, STORE, item["url"], item["price"])
                        conn.commit()
                        saved += 1
                    except Exception as e:
                        conn.rollback()
                        print(f"[{STORE}] FAILED to save '{item['title']}': {e}")
                        failed += 1

                    await asyncio.sleep(random.uniform(3, 6))
    finally:
        conn.close()

    print(f"[{STORE}] done. found={found} saved={saved} failed={failed}")


if __name__ == "__main__":
    asyncio.run(run())
