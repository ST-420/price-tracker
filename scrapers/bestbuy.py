"""Discovers and price-checks phones/laptops on Best Buy. Same approach as
amazon.py — one search-results page yields many products' title+price+link
at once. See that file's docstring for the overall design.

Best Buy's search results page embeds each product's real manufacturer model
number in an internal JSON blob (Apollo GraphQL cache), so — unlike Amazon —
no extra product-page visit is needed. That's fortunate, because Best Buy's
individual product pages are blocked entirely from this environment (tested
against several real product URLs, all failed with a network-level error).
"""

import asyncio
import random
import re

from bs4 import BeautifulSoup

from . import attributes, db
from .fetch import fetch_html
from .queries import CATALOG_CAP, SEARCH_QUERIES

STORE = "bestbuy"
BASE_URL = "https://www.bestbuy.com"


SKIP_TITLE_WORDS = ("renewed", "refurbished", "used", "open box", "pre-owned", "geek squad certified")


CANDIDATES_PER_TERM = 5


def extract_products(html: str) -> list[dict]:
    """Returns genuine, non-refurbished organic results, page order (which is
    Best Buy's own relevance ranking). Callers process the top few (see
    CANDIDATES_PER_TERM) — with just one, there's almost no chance it happens
    to be the exact same configuration Amazon's top result for the same term
    is, so barely anything ever cross-store-matches. More candidates means
    more chance of a real overlap for the matching rules to find. No extra
    request cost here (unlike amazon.py) since price/model-number is already
    on this page for every card."""
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select('div[data-testid="ECL-ProductCard"]'):
        link = card.select_one("h3.product-list-item-link a")
        price_el = card.select_one('div[data-testid="price-block-customer-price"] span.sr-only')
        if not (link and price_el):
            continue

        title = link.get("title") or link.get_text(strip=True)
        price_text = price_el.get_text(strip=True)
        price_match = re.search(r"[\d,]+\.\d{2}", price_text)
        if not title or not price_match:
            continue
        if any(word in title.lower() for word in SKIP_TITLE_WORDS):
            continue

        href = link["href"]
        url = href if href.startswith("http") else BASE_URL + href
        img = card.select_one("img")
        items.append({
            "title": title.strip(),
            "price": float(price_match.group(0).replace(",", "")),
            "url": url.split("?")[0],
            "image_url": img.get("src") if img else None,
        })
    return items


def extract_model_numbers(html: str) -> dict[str, str]:
    """Maps normalized title -> manufacturer model number, parsed from the
    page's embedded JSON (each product's "short" title is immediately
    followed by its manufacturer.modelNumber in that data)."""
    mapping = {}
    for m in re.finditer(r'"short":"((?:[^"\\]|\\.)*)".*?"modelNumber":"([^"]*)"', html, re.DOTALL):
        short_title = m.group(1).replace('\\"', '"').replace("\\\\", "\\")
        normalized = re.sub(r"\s+", " ", short_title).strip().lower()
        mapping[normalized] = m.group(2)
    return mapping


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

                    url = f"{BASE_URL}/site/searchpage.jsp?st={term.replace(' ', '+')}"
                    ok, html = await fetch_html(url, wait_for_selector='div[data-testid="ECL-ProductCard"]')
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

                    model_numbers = extract_model_numbers(html)
                    for item in items[:CANDIDATES_PER_TERM]:
                        normalized_title = re.sub(r"\s+", " ", item["title"]).strip().lower()
                        model_number = model_numbers.get(normalized_title)

                        attrs = attributes.parse(item["title"], brand_hint=term)

                        try:
                            product_id, match_method = db.match_or_create_listing(
                                cur, category, STORE, item["url"], item["price"], item["title"],
                                None, model_number, attrs, item.get("image_url"),
                            )
                            db.upsert_listing_price(
                                cur, product_id, STORE, item["url"], item["price"],
                                match_method, None, model_number, attrs,
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
