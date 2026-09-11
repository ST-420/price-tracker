-- One row per product. For manually-seeded rows (products.csv), `brand` and
-- `model` are real values (e.g. "Apple" / "iPhone 15"). For scraper-discovered
-- rows (Phase 3), `brand`/`model` are parsed from whichever listing created
-- this product (see scrapers/attributes.py) — display fields only; they are
-- NOT the cross-store match key (see listings.match_method below), since
-- storage variants of the same model are intentionally kept as separate
-- products, so brand+model alone isn't unique.
CREATE TABLE IF NOT EXISTS products (
    id bigserial PRIMARY KEY,
    brand text NOT NULL,
    model text NOT NULL,
    category text NOT NULL CHECK (category IN ('phone', 'laptop')),
    name text NOT NULL,
    image_url text,
    specs jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- One row per (product, store) pair — where that product is listed and its
-- current price. A listing is linked to a product's other-store listings by
-- one of three rules, checked in order (see scrapers/db.py):
--   1. upc matches exactly
--   2. model_number matches exactly (normalized: uppercase, no spaces/dashes)
--   3. brand + parsed model name (stored in `products.model`) + storage all
--      match exactly (color is allowed to differ; storage/ram mismatch is a
--      hard reject)
-- match_method records which rule fired (null = no match; this listing got
-- its own unlinked product row). match_confidence is illustrative, ranked by
-- rule: upc=1.0, model_number=0.9, attributes=0.7.
CREATE TABLE IF NOT EXISTS listings (
    id bigserial PRIMARY KEY,
    product_id bigint NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    store text NOT NULL CHECK (store IN ('amazon', 'bestbuy', 'walmart')),
    store_product_id text,
    url text NOT NULL,
    current_price numeric(10, 2),
    in_stock boolean,
    last_checked timestamptz,
    upc text,
    model_number text,
    brand text,
    model_name text,
    storage text,
    ram text,
    screen_size text,
    color text,
    match_method text CHECK (match_method IN ('upc', 'model_number', 'attributes')),
    match_confidence numeric(3, 2),
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
