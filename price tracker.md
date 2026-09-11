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
- A listing is matched to an existing product on another store using rules checked in this order (never on raw title similarity): (1) UPC exact match, (2) model number exact match (normalized), (3) brand + parsed model name + storage all match exactly (color may differ; an explicit RAM mismatch rejects). No match on any rule → the listing gets its own unlinked product row rather than being force-paired. `listings.match_method` records which rule fired (or null). See Stack for what each store actually exposes — Amazon and Best Buy each only expose one of UPC/model number, so in practice rule 3 (attributes) is what bridges them; rules 1-2 mostly guard against ever mis-linking two different products, more than they actively connect Amazon-Best Buy pairs today
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
  - Amazon: search page doesn't expose UPC/model number, so its top candidate's own product page is also fetched (one extra request) for UPC + Brand — Amazon has no consistent alphanumeric model-number field across categories, so UPC is its strong identifier
  - Best Buy: the manufacturer's real model number is already embedded in the search page's own JSON (no extra request needed) — but its product pages are completely blocked from this environment (tested against several real URLs, all failed), so UPC isn't obtainable here
  - `scrapers/attributes.py` parses brand/model name/storage/RAM/screen size/color out of a title (best-effort — see Scope for how this feeds rule 3)
  - `scrapers/db.py` holds the matching logic (see Scope) and price-recording; `scrapers/fetch.py` holds the shared crawl4ai fetch-with-retry helper; `scrapers/run_all.py` runs all three stores, isolating one store's crash from the others (this is what Phase 4's scheduler will call)
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
- [x] GitHub Actions workflow runs all three fetchers twice daily — `.github/workflows/daily-price-check.yml`, 9am and 9pm UTC, also runnable manually from the Actions tab
- [x] Store Supabase and API keys as GitHub Secrets — `SUPABASE_DB_URL`
- [ ] Confirm price_history grows by one row per listing per run — manual runs tested end-to-end (real rows landed in Supabase, including a listing checked 4x in one session showing 4 distinct price_history points); still need to see the scheduled (not manually-triggered) runs fire and repeat over a few real days
- [x] One-time historical backfill from Wayback Machine — `scripts/backfill_wayback.py` (not part of the daily job). Pulls real archived snapshots of each Amazon/Best Buy product page from the last ~180 days and extracts their price, tagged `source='wayback'` in `price_history` (vs `'live'` for the regular scraper) — gives the chart real history immediately instead of waiting weeks for the daily job alone
- Start the scheduler as early as possible — the chart needs weeks of `live` data on top of whatever the one-time backfill covers

### Phase 5 — Website
- [x] Search page: text box, results list — `src/app/page.tsx`
- [x] Product page: details, table of 3 stores with price + link, cheapest highlighted — `src/app/product/[id]/page.tsx`. Only listings matched by rules 1-3 are shown (see Scope) — an unmatched single-store listing shows "No verified cross-store listing yet" instead
- [x] Price history chart: one line per store — `src/components/PriceChart.tsx`
- [x] Deploy to Vercel — live at https://price-tracker-opal-seven.vercel.app (GitHub auto-deploy-on-push isn't connected yet — Vercel's GitHub App connection failed non-interactively; deploys for now go out via `vercel deploy --prod` when asked)

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
