"""Shared database helpers used by every store scraper: finding or creating a
product, and recording a listing's current price + price history row.

Cross-store matching: an earlier version fuzzy-matched each store's scraped
title against existing products' names. In practice this never worked —
real listing titles are packed with store-specific marketing copy (e.g.
"XPS 13 9360, 13.4" 2.5K Touchscreen, Core 5 320, 8GB DDR5, 512GB SSD |
Premium AI PC...") that differs enough between stores that fuzzy comparison
never crossed the similarity threshold, so every store's listing ended up
as its own isolated product with zero cross-store matches. Since every
store is scraped using the same shared list of search terms (queries.py),
matching on that term instead is deterministic and guaranteed to work: two
stores' results for the same term are, by construction, the same product.
"""

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT / ".env")


def connect():
    return psycopg2.connect(os.environ["SUPABASE_DB_URL"], connect_timeout=10)


def catalog_size(cur) -> int:
    cur.execute("SELECT count(*) FROM products;")
    return cur.fetchone()[0]


def find_or_create_product(cur, term: str, category: str, display_title: str, image_url: str | None = None) -> int:
    """Looks up a product by the search term that discovered it (stored in
    `model`) and category. Returns the matched product's id, or creates a new
    product — using `display_title` as the human-readable name — and returns
    its id."""
    cur.execute("SELECT id FROM products WHERE category = %s AND model = %s;", (category, term))
    row = cur.fetchone()
    if row:
        return row[0]

    # New product: brand is a best-effort guess (first word of the title).
    brand = display_title.split()[0] if display_title else term.split()[0]
    cur.execute(
        """
        INSERT INTO products (brand, model, category, name, image_url)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id;
        """,
        (brand, term, category, display_title, image_url),
    )
    return cur.fetchone()[0]


def upsert_listing_price(cur, product_id: int, store: str, url: str, price: float):
    cur.execute(
        """
        INSERT INTO listings (product_id, store, url, current_price, in_stock, last_checked)
        VALUES (%s, %s, %s, %s, true, now())
        ON CONFLICT (product_id, store) DO UPDATE
            SET url = EXCLUDED.url,
                current_price = EXCLUDED.current_price,
                in_stock = true,
                last_checked = now()
        RETURNING id;
        """,
        (product_id, store, url, price),
    )
    listing_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO price_history (listing_id, price) VALUES (%s, %s);",
        (listing_id, price),
    )
