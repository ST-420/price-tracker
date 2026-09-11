"""Shared database helpers used by every store scraper: matching a scraped
listing to an existing product on another store (or creating a new,
unlinked product if nothing matches), and recording price + price history.

Matching rules, checked in this order (see price tracker.md > Scope):
  1. upc matches an existing listing (any store) exactly -> match_method="upc"
  2. model_number matches, normalized (uppercase, no spaces/dashes) ->
     match_method="model_number"
  3. brand + model_name + storage all match exactly (color may differ; an
     explicit ram mismatch rejects even if the rest matches) ->
     match_method="attributes"
  4. nothing matches -> new, unlinked product; match_method is left null

Never matches on raw title similarity — see scrapers/attributes.py for how
brand/model_name/storage/ram/color are parsed out of a title first.
"""

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

from .attributes import normalize_model_number

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

CONFIDENCE = {"upc": 1.0, "model_number": 0.9, "attributes": 0.7}


def connect():
    return psycopg2.connect(os.environ["SUPABASE_DB_URL"], connect_timeout=10)


def catalog_size(cur) -> int:
    cur.execute("SELECT count(*) FROM products;")
    return cur.fetchone()[0]


def _find_match_by_upc(cur, category: str, store: str, upc: str):
    if not upc:
        return None
    cur.execute(
        """
        SELECT l.product_id FROM listings l JOIN products p ON p.id = l.product_id
        WHERE p.category = %s AND l.store != %s AND l.upc = %s
        LIMIT 1;
        """,
        (category, store, upc),
    )
    row = cur.fetchone()
    return row[0] if row else None


def _find_match_by_model_number(cur, category: str, store: str, model_number: str):
    if not model_number:
        return None
    normalized = normalize_model_number(model_number)
    cur.execute(
        """
        SELECT l.product_id, l.model_number FROM listings l JOIN products p ON p.id = l.product_id
        WHERE p.category = %s AND l.store != %s AND l.model_number IS NOT NULL;
        """,
        (category, store),
    )
    for product_id, existing_number in cur.fetchall():
        if normalize_model_number(existing_number) == normalized:
            return product_id
    return None


def _find_match_by_attributes(cur, category: str, store: str, attrs: dict):
    brand, model_name, storage, ram = (
        attrs.get("brand"), attrs.get("model_name"), attrs.get("storage"), attrs.get("ram")
    )
    if not (brand and model_name and storage):
        return None  # can't confirm an exact match without all three present

    cur.execute(
        """
        SELECT l.product_id, l.ram FROM listings l JOIN products p ON p.id = l.product_id
        WHERE p.category = %s AND l.store != %s
            AND lower(l.brand) = lower(%s)
            AND lower(l.model_name) = lower(%s)
            AND lower(l.storage) = lower(%s);
        """,
        (category, store, brand, model_name, storage),
    )
    for product_id, existing_ram in cur.fetchall():
        if ram and existing_ram and ram.lower() != existing_ram.lower():
            continue  # explicit ram mismatch rejects this candidate
        return product_id
    return None


def match_or_create_listing(
    cur,
    category: str,
    store: str,
    url: str,
    price: float,
    title: str,
    upc: str | None,
    model_number: str | None,
    attrs: dict,
) -> tuple[int, str | None]:
    """Finds a matching product for this listing (rules 1-3) or creates a new
    one (rule 4). Returns (product_id, match_method)."""
    match_method = None
    product_id = _find_match_by_upc(cur, category, store, upc)
    if product_id:
        match_method = "upc"
    else:
        product_id = _find_match_by_model_number(cur, category, store, model_number)
        if product_id:
            match_method = "model_number"
        else:
            product_id = _find_match_by_attributes(cur, category, store, attrs)
            if product_id:
                match_method = "attributes"

    if not product_id:
        brand = attrs.get("brand") or title.split()[0]
        model_name = attrs.get("model_name") or title
        cur.execute(
            """
            INSERT INTO products (brand, model, category, name)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
            """,
            (brand, model_name, category, title),
        )
        product_id = cur.fetchone()[0]

    return product_id, match_method


def upsert_listing_price(
    cur,
    product_id: int,
    store: str,
    url: str,
    price: float,
    match_method: str | None,
    upc: str | None,
    model_number: str | None,
    attrs: dict,
):
    confidence = CONFIDENCE.get(match_method)
    cur.execute(
        """
        INSERT INTO listings (
            product_id, store, url, current_price, in_stock, last_checked,
            upc, model_number, brand, model_name, storage, ram, screen_size, color,
            match_method, match_confidence
        )
        VALUES (%s, %s, %s, %s, true, now(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (product_id, store) DO UPDATE
            SET url = EXCLUDED.url,
                current_price = EXCLUDED.current_price,
                in_stock = true,
                last_checked = now(),
                upc = EXCLUDED.upc,
                model_number = EXCLUDED.model_number,
                brand = EXCLUDED.brand,
                model_name = EXCLUDED.model_name,
                storage = EXCLUDED.storage,
                ram = EXCLUDED.ram,
                screen_size = EXCLUDED.screen_size,
                color = EXCLUDED.color,
                match_method = EXCLUDED.match_method,
                match_confidence = EXCLUDED.match_confidence
        RETURNING id;
        """,
        (
            product_id, store, url, price, upc, model_number,
            attrs.get("brand"), attrs.get("model_name"), attrs.get("storage"),
            attrs.get("ram"), attrs.get("screen_size"), attrs.get("color"),
            match_method, confidence,
        ),
    )
    listing_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO price_history (listing_id, price) VALUES (%s, %s);",
        (listing_id, price),
    )
