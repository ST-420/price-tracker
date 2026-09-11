"""Runs schema.sql against the Supabase database to create the products,
listings, and price_history tables (safe to re-run — uses CREATE TABLE IF NOT EXISTS)."""

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT / ".env")


def main():
    db_url = os.environ["SUPABASE_DB_URL"]
    schema_sql = (ROOT / "schema.sql").read_text()

    conn = psycopg2.connect(db_url, connect_timeout=10)
    try:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        conn.commit()
        print("Tables created: products, listings, price_history")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
