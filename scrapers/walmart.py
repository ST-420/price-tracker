"""Discovers and price-checks phones/laptops on Walmart. Same approach as
amazon.py and bestbuy.py — see that file's docstring.

STATUS: currently blocked. Walmart's search page returns an interactive
"press and hold to verify you're human" challenge for every request tried
so far from this environment (even with a warmed-up browser session), and
that's not something this project will try to script around. This file
still runs safely — it logs the block and moves on to the next term — so
that one blocked store doesn't stop the other scrapers. It also runs the
CSS extraction below whenever a page *does* get through, and the run()
function reports plainly if it never once got past the block. Extraction
selectors here are unverified — see BESTBUY_STYLE_NOTE below.
"""

import asyncio
import random
import re

from bs4 import BeautifulSoup

from . import attributes, db
from .fetch import fetch_html
from .queries import CATALOG_CAP, SEARCH_QUERIES

STORE = "walmart"
BASE_URL = "https://www.walmart.com"

# Unverified — Walmart has never returned real search results to this
# scraper to check against. These are a best guess based on Walmart's public
# markup conventions; whoever gets a real page through (e.g. testing from a
# home network) should confirm/fix these against actual HTML.
def extract_products(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select('[data-item-id]'):
        link = card.select_one('a[link-identifier="linkText"]') or card.select_one("a")
        price_el = card.select_one('[data-automation-id="product-price"]')
        if not (link and price_el):
            continue

        title = link.get_text(strip=True)
        price_text = price_el.get_text(strip=True)
        price_match = re.search(r"[\d,]+\.\d{2}", price_text)
        if not title or not price_match:
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
    found, saved, failed, blocked_count = 0, 0, 0, 0
    try:
        with conn.cursor() as cur:
            for category, terms in SEARCH_QUERIES.items():
                for term in terms:
                    if db.catalog_size(cur) >= CATALOG_CAP:
                        print(f"[{STORE}] catalog cap ({CATALOG_CAP}) reached, stopping discovery")
                        break

                    url = f"{BASE_URL}/search?q={term.replace(' ', '+')}"
                    ok, html = await fetch_html(url, wait_for_selector="[data-item-id]")
                    if not ok:
                        print(f"[{STORE}] BLOCKED or failed: {term}")
                        failed += 1
                        blocked_count += 1
                        await asyncio.sleep(random.uniform(3, 6))
                        continue

                    items = extract_products(html)
                    print(f"[{STORE}] {term}: {len(items)} candidates found")
                    if not items:
                        await asyncio.sleep(random.uniform(3, 6))
                        continue
                    found += 1

                    item = items[0]  # best organic match for this search term
                    attrs = attributes.parse(item["title"], brand_hint=term)
                    try:
                        product_id, match_method = db.match_or_create_listing(
                            cur, category, STORE, item["url"], item["price"], item["title"],
                            None, None, attrs,
                        )
                        db.upsert_listing_price(
                            cur, product_id, STORE, item["url"], item["price"],
                            match_method, None, None, attrs,
                        )
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
    if blocked_count > 0 and saved == 0:
        print(f"[{STORE}] WARNING: every request was blocked. Walmart is not working from this environment.")


if __name__ == "__main__":
    asyncio.run(run())
