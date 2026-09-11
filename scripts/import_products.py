"""Reads products.csv and loads it into the products and listings tables.

Each CSV row becomes one product. A listing row is only created for a store
(amazon/bestbuy/walmart) when that row's URL column is filled in — rows with
a blank URL are skipped for that store. Safe to re-run: existing products
(matched by brand+model) and listings (matched by product+store) are updated
in place instead of duplicated.
"""

import csv
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

STORES = ["amazon", "bestbuy", "walmart"]


def main():
    db_url = os.environ["SUPABASE_DB_URL"]
    conn = psycopg2.connect(db_url, connect_timeout=10)

    products_seen = 0
    listings_seen = 0

    try:
        with conn.cursor() as cur, open(ROOT / "products.csv", newline="") as f:
            for row in csv.DictReader(f):
                brand = row["brand"].strip()
                model = row["model"].strip()
                category = row["category"].strip()
                name = f"{brand} {model}"

                cur.execute(
                    """
                    INSERT INTO products (brand, model, category, name)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (brand, model) DO UPDATE
                        SET category = EXCLUDED.category, name = EXCLUDED.name
                    RETURNING id;
                    """,
                    (brand, model, category, name),
                )
                product_id = cur.fetchone()[0]
                products_seen += 1

                for store in STORES:
                    url = row.get(f"{store}_url", "").strip()
                    if not url:
                        continue
                    cur.execute(
                        """
                        INSERT INTO listings (product_id, store, url)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (product_id, store) DO UPDATE
                            SET url = EXCLUDED.url;
                        """,
                        (product_id, store, url),
                    )
                    listings_seen += 1

        conn.commit()
        print(f"Imported {products_seen} products, {listings_seen} listings.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
