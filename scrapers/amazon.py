"""Discovers and price-checks phones/laptops on Amazon.

For each search term in queries.py, fetches one search-results page (which
already carries title + price + link for ~20-60 products at once — far
cheaper than visiting every product page individually) and takes the top
few genuine (non-sponsored, non-refurbished) results (CANDIDATES_PER_TERM).
For each one, visits that product's own detail page for its UPC and Brand
fields (Amazon's search results don't expose these; its product pages
reliably do — see price tracker.md > Scope for why this is the identifier
used for matching). Logs and skips anything that fails instead of crashing
the whole run.
"""

import asyncio
import random
import re

from bs4 import BeautifulSoup

from . import attributes, db
from .fetch import fetch_html
from .queries import CATALOG_CAP, SEARCH_QUERIES

STORE = "amazon"
BASE_URL = "https://www.amazon.com"


SKIP_TITLE_WORDS = ("renewed", "refurbished", "used", "open box", "pre-owned")


CANDIDATES_PER_TERM = 3


def extract_products(html: str) -> list[dict]:
    """Returns genuine (non-sponsored, non-refurbished) organic results, best
    match first. Callers process the top few (see CANDIDATES_PER_TERM) — with
    just one, there's almost no chance it happens to be the exact same
    configuration Best Buy's top result for the same term is, so barely
    anything ever cross-store-matches. More candidates means more chance of a
    real overlap for the matching rules to find."""
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
        img = card.select_one("img.s-image")
        items.append({
            "title": title.strip(),
            "price": float(price_match.group(0).replace(",", "")),
            "url": url.split("?")[0],
            "image_url": img.get("src") if img else None,
        })
    return items


def extract_detail_page_data(html: str) -> dict:
    """Reads Amazon's product-details key/value tables for UPC and Brand.
    Amazon doesn't have a consistent alphanumeric "model number" field across
    categories the way Best Buy does, so this project uses UPC as Amazon's
    strong identifier (rule 1) instead."""
    soup = BeautifulSoup(html, "html.parser")
    kv = {}
    for table_id in ("#poExpander", "#prodDetails"):
        el = soup.select_one(table_id)
        if not el:
            continue
        for tr in el.select("tr"):
            cells = tr.select("td, th")
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True).lower()
                value = cells[1].get_text(strip=True)
                kv[key] = value
    return {"upc": kv.get("upc"), "brand": kv.get("brand")}


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

                    for item in items[:CANDIDATES_PER_TERM]:
                        attrs = attributes.parse(item["title"], brand_hint=term)
                        upc = None
                        await asyncio.sleep(random.uniform(2, 4))
                        detail_ok, detail_html = await fetch_html(
                            item["url"], wait_for_selector="#productTitle", magic=False
                        )
                        if detail_ok:
                            detail = extract_detail_page_data(detail_html)
                            upc = detail["upc"]
                            if detail["brand"]:
                                attrs["brand"] = detail["brand"]
                        else:
                            print(f"[{STORE}] detail page failed for '{item['title']}' — matching on attributes only")

                        try:
                            product_id, match_method = db.match_or_create_listing(
                                cur, category, STORE, item["url"], item["price"], item["title"],
                                upc, None, attrs, item.get("image_url"),
                            )
                            db.upsert_listing_price(
                                cur, product_id, STORE, item["url"], item["price"],
                                match_method, upc, None, attrs,
                            )
                            conn.commit()
                            saved += 1
                            print(f"[{STORE}] saved '{item['title'][:50]}' match_method={match_method}")
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
