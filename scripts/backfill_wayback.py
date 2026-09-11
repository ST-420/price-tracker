"""One-time backfill: for every Amazon/Best Buy listing already in the
database, pulls whatever Wayback Machine snapshots exist for its product
page over the last ~6 months, extracts the price from each, and inserts
them into price_history with source='wayback' — so the price chart has
real history before the daily scraper (source='live') has had time to
accumulate its own.

Not part of the daily job — run manually, once:
    python3 scripts/backfill_wayback.py

Walmart is skipped (it has no working listings yet — see price tracker.md).
"""

import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg2
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

LOOKBACK_DAYS = 180
MAX_SNAPSHOTS_PER_LISTING = 20
CDX_API = "https://web.archive.org/cdx/search/cdx"
HEADERS = {"User-Agent": "price-tracker-backfill/1.0 (personal project)"}


def canonicalize_url(store: str, url: str) -> str:
    if store == "amazon":
        # Strip Amazon's "/ref=..." position-tracking suffix — snapshots are
        # indexed under the canonical /dp/ASIN URL, not this search-result-
        # position-specific variant, so leaving it in finds zero snapshots.
        return re.sub(r"/ref=[^/?]*", "", url)
    return url


def list_snapshots(url: str) -> list[tuple[str, str]]:
    """Returns [(timestamp, original_url), ...] for snapshots in the lookback
    window, deduplicated by content (collapse=digest) and downsampled to
    MAX_SNAPSHOTS_PER_LISTING if there are more than that available."""
    since = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).strftime("%Y%m%d")
    until = datetime.now(timezone.utc).strftime("%Y%m%d")
    resp = requests.get(
        CDX_API,
        params={
            "url": url,
            "from": since,
            "to": until,
            "output": "json",
            "collapse": "digest",
            "filter": "statuscode:200",
            "limit": 200,
        },
        headers=HEADERS,
        timeout=20,
    )
    resp.raise_for_status()
    rows = resp.json()
    if len(rows) <= 1:
        return []
    snapshots = [(r[1], r[2]) for r in rows[1:]]  # skip header row
    if len(snapshots) > MAX_SNAPSHOTS_PER_LISTING:
        step = len(snapshots) / MAX_SNAPSHOTS_PER_LISTING
        snapshots = [snapshots[int(i * step)] for i in range(MAX_SNAPSHOTS_PER_LISTING)]
    return snapshots


def fetch_snapshot_html(timestamp: str, original_url: str) -> str | None:
    snapshot_url = f"https://web.archive.org/web/{timestamp}/{original_url}"
    resp = requests.get(snapshot_url, headers=HEADERS, timeout=30)
    if resp.status_code != 200:
        return None
    return resp.text


def extract_amazon_price(html: str) -> float | None:
    soup = BeautifulSoup(html, "html.parser")
    el = soup.select_one("#corePrice_feature_div span.a-offscreen") or soup.select_one(
        ".a-price span.a-offscreen"
    )
    if not el:
        return None
    m = re.search(r"[\d,]+\.\d{2}", el.get_text(strip=True))
    return float(m.group(0).replace(",", "")) if m else None


def extract_bestbuy_price(html: str) -> float | None:
    # The page's own analytics-metadata tag carries this exact SKU's price as
    # clean JSON — far more reliable than scanning for "$X.XX" on the page,
    # which also shows prices for unrelated "related items" carousels.
    m = re.search(r"analytics-metadata\" content=\"[^\"]*?price&quot;:&quot;([\d.]+)&quot;", html)
    return float(m.group(1)) if m else None


EXTRACTORS = {"amazon": extract_amazon_price, "bestbuy": extract_bestbuy_price}


def timestamp_to_datetime(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)


def main():
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], connect_timeout=10)
    products_backfilled = set()
    total_points = 0

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, product_id, store, url FROM listings WHERE store IN ('amazon', 'bestbuy') ORDER BY id;"
            )
            listings = cur.fetchall()

        print(f"Backfilling {len(listings)} listings from Wayback Machine (last {LOOKBACK_DAYS} days)...")

        for listing_id, product_id, store, url in listings:
            canonical = canonicalize_url(store, url)
            try:
                snapshots = list_snapshots(canonical)
            except Exception as e:
                print(f"[{store}] listing {listing_id}: CDX lookup failed: {e}")
                continue

            if not snapshots:
                print(f"[{store}] listing {listing_id}: no snapshots found")
                continue

            inserted_for_listing = 0
            for timestamp, original_url in snapshots:
                recorded_at = timestamp_to_datetime(timestamp)
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT 1 FROM price_history WHERE listing_id = %s AND source = 'wayback' AND recorded_at = %s;",
                        (listing_id, recorded_at),
                    )
                    if cur.fetchone():
                        continue  # already backfilled this snapshot (safe to re-run the script)

                try:
                    html = fetch_snapshot_html(timestamp, original_url)
                    price = EXTRACTORS[store](html) if html else None
                except Exception as e:
                    print(f"[{store}] listing {listing_id} @ {timestamp}: fetch/parse failed: {e}")
                    price = None

                if price is not None:
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO price_history (listing_id, price, recorded_at, source) VALUES (%s, %s, %s, 'wayback');",
                            (listing_id, price, recorded_at),
                        )
                    conn.commit()
                    inserted_for_listing += 1
                    total_points += 1

                time.sleep(1)  # go easy on archive.org

            if inserted_for_listing:
                products_backfilled.add(product_id)
                print(f"[{store}] listing {listing_id}: {inserted_for_listing} price points backfilled")
            else:
                print(f"[{store}] listing {listing_id}: {len(snapshots)} snapshots found, none had an extractable price")
    finally:
        conn.close()

    print(f"\nDone. {len(products_backfilled)} products backfilled, {total_points} total price points inserted.")


if __name__ == "__main__":
    main()
