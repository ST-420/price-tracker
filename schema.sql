-- One row per product. For manually-seeded rows (products.csv), `model` is a
-- real model name (e.g. "iPhone 15"). For scraper-discovered rows (Phase 3),
-- `model` holds the search term that found it (e.g. "dell xps 13") — reusing
-- that term as the match key is what lets the same product discovered on two
-- different stores land on one row instead of two (see scrapers/db.py).
CREATE TABLE IF NOT EXISTS products (
    id bigserial PRIMARY KEY,
    brand text NOT NULL,
    model text NOT NULL,
    category text NOT NULL CHECK (category IN ('phone', 'laptop')),
    name text NOT NULL,
    image_url text,
    specs jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (brand, model),
    UNIQUE (category, model)
);

-- One row per (product, store) pair — where that product is listed and its current price.
CREATE TABLE IF NOT EXISTS listings (
    id bigserial PRIMARY KEY,
    product_id bigint NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    store text NOT NULL CHECK (store IN ('amazon', 'bestbuy', 'walmart')),
    store_product_id text,
    url text NOT NULL,
    current_price numeric(10, 2),
    in_stock boolean,
    last_checked timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (product_id, store)
);

-- One row per price check — builds the price-over-time chart.
CREATE TABLE IF NOT EXISTS price_history (
    id bigserial PRIMARY KEY,
    listing_id bigint NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    price numeric(10, 2) NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_listings_product_id ON listings(product_id);
CREATE INDEX IF NOT EXISTS idx_price_history_listing_id ON price_history(listing_id);
