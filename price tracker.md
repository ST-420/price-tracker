# Price Tracker — Project Plan

## What this is
A website where a user searches a phone or laptop and sees:
1. Product details
2. Which of Amazon, Best Buy, and Walmart list it
3. Current price on each site, cheapest highlighted
4. Link to the product on each site
5. Price history chart per site (like camelcamelcamel, but across three stores)

## Scope (prototype)
- Categories: mobile phones and laptops only
- Stores: Amazon.com, BestBuy.com, Walmart.com
- Catalog grows via crawling/discovery (not just the manually-seeded `products.csv`), soft-capped around 500 products to keep scraping volume manageable
- A product found on one store is matched to the "same" product on another store by the shared search term that discovered it (e.g. both stores' results for "dell xps 13" land on one product row) — not a shared barcode/ID. This replaced an earlier fuzzy title-matching approach that turned out not to work in practice: real listing titles are packed with store-specific marketing copy that differs too much between stores for fuzzy comparison to reliably recognize the same product
- Zero infrastructure cost — free tiers only
- Owner is a non-coder. Explain every step in plain English. Ask before running anything destructive.

## Stack
- Website + API: Next.js, deployed on Vercel
- Database: Supabase (Postgres)
- Price fetchers/discovery: one Python script per store (`scrapers/amazon.py`, `scrapers/bestbuy.py`, `scrapers/walmart.py`) using crawl4ai (open-source, real headless-browser scraper). Free, self-hosted, no daily request cap — unlike hosted scraping APIs, which were considered and ruled out:
  - krawly.io: free tier capped at 30 requests/day, not enough for our volume
  - Apify: has ready-made Amazon/Walmart/Best Buy scrapers that dodge bot-detection better, but daily automated use costs real money past the $5/month free credit (e.g. Amazon actor alone ≈ $37/month at 200 products/day) — ruled out to keep the project zero-cost
  - (Scrapy was also tried alongside crawl4ai for discovery crawling, but dropped — its Twisted/pyOpenSSL dependencies conflict with modern `cryptography` and fail to install on this machine; crawl4ai alone covers both discovery and price-fetching anyway)
  - Each store's script fetches one search-results page per term in `scrapers/queries.py` — a single page load carries title+price+link for ~4-20 products at once, so this covers discovery *and* daily price-checking in one pass rather than visiting hundreds of individual product pages
  - `scrapers/db.py` holds the shared product-matching (by search term, see Scope) and price-recording logic; `scrapers/fetch.py` holds the shared crawl4ai fetch-with-retry helper; `scrapers/run_all.py` runs all three stores, isolating one store's crash from the others (this is what Phase 4's scheduler will call)
- Scheduler: GitHub Actions, runs fetchers once a day
- Secrets: `.env` file locally, GitHub Secrets and Vercel env vars in production. Never hardcode keys.

## Accounts
- GitHub — created
- Supabase — created
- Vercel — created
- Best Buy Developer — API key requested, waiting for approval. Not needed for now — see Data sources.

## How accounts connect
- GitHub and Vercel: Claude Code runs a login command, the browser opens, user clicks Authorize
- Supabase: user pastes connection string into `.env`
- Keys are never pasted into chat

## Data sources
- Amazon: scraper (crawl4ai + real headless browser). Working — a 20-search-term run typically saves ~18-19/20.
- Best Buy: scraper, same approach (using a scraper for now instead of the official API; can switch to the API later once the key comes through). Working but less consistent — typically saves ~10-12/20 per run; the rest fail because Best Buy's product grid sometimes takes too long to render or the request gets rate-limited. This is expected scraper variability, not a bug to chase further for the prototype.
- Walmart: scraper, same approach. **Not working** — Walmart's search page returns an interactive "press and hold to verify you're human" challenge on nearly every request from this environment, even with a warmed-up browser session. This project won't try to script around an interactive human-verification widget. `scrapers/walmart.py` exists and runs safely (logs the block, doesn't crash), but currently contributes no data. Worth periodically retrying, or testing from a residential (non-cloud) network connection.

## Database tables
- `products` — id, brand, model, category (phone/laptop), name, image_url, specs (json)
- `listings` — id, product_id, store (amazon/bestbuy/walmart), store_product_id, url, current_price, in_stock, last_checked
- `price_history` — id, listing_id, price, recorded_at

## Phases

### Phase 1 — Setup
- [x] Create accounts (GitHub, Supabase, Vercel)
- [ ] Best Buy API key (requested, pending — not needed for now, using a scraper instead)
- [x] Create `products.csv` template (headers + example rows; ~100 real rows to be filled in during Phase 2 research)
- [x] Initialize Next.js project, connect to GitHub — https://github.com/ST-420/price-tracker

### Phase 2 — Database
- [x] Create the three tables in Supabase — `schema.sql`, run via `scripts/create_tables.py`
- [x] Write a script that imports `products.csv` into `products` and `listings` — `scripts/import_products.py`
- [x] Verify rows appear in the Supabase dashboard — 4 template products confirmed (no listings yet, since URLs are still blank)

### Phase 3 — Discovery + price fetchers (`scrapers/`, using crawl4ai)
- [x] `scrapers/amazon.py` — searches each term in `queries.py`, saves the top genuine (non-sponsored, non-refurbished) result per term. Working: ~18-19/20 terms saved per run.
- [x] `scrapers/bestbuy.py` — same approach. Working but less reliable: ~10-12/20 terms saved per run (see Data sources).
- [x] `scrapers/walmart.py` — same approach, but Walmart blocks nearly every request (see Data sources). Runs safely without crashing; saves 0 rows for now.
- [x] `scrapers/db.py` — matches products across stores by shared search term (see Scope), records price + price history
- [x] `scrapers/fetch.py` — shared crawl4ai fetch helper with retries and bot-block detection
- [x] `scrapers/run_all.py` — runs all three stores in sequence; one store crashing doesn't stop the others
- [x] Verified end-to-end: after a real run, 10 products have genuine listings on both Amazon and Best Buy with different real prices — the core "compare prices across stores" feature works
- Not done in this phase: Best Buy's official API integration (deferred — see Data sources), a review/undo step for mismatched products (none exists yet)

### Phase 4 — Scheduler
- [ ] GitHub Actions workflow runs all three fetchers daily
- [ ] Store Supabase and API keys as GitHub Secrets
- [ ] Confirm price_history grows by one row per listing per day
- Start this as early as possible — the chart needs weeks of data

### Phase 5 — Website
- [ ] Search page: text box, results list
- [ ] Product page: details, table of 3 stores with price + link, cheapest highlighted
- [ ] Price history chart: one line per store
- [ ] Deploy to Vercel

### Phase 6 — Demo
- [ ] Let scheduler run 2–3 weeks
- [ ] Spot-check 10 products against the live sites
- [ ] Demo

## Definition of done
Search a seeded product → see details, prices on all three stores with links, cheapest flagged, chart with at least 2 weeks of history.

## Rules for Claude Code
- Work one phase at a time. Do not start the next phase until the current one is verified.
- Keep it simple. No extra features unless asked.
- Explain what each file does when you create it.
- Read secrets from `.env`; never print them or commit them.
- Commit to GitHub after each phase.
