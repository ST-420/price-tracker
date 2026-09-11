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
- ~100 seeded products, no open-ended discovery
- Zero infrastructure cost — free tiers only
- Owner is a non-coder. Explain every step in plain English. Ask before running anything destructive.

## Stack
- Website + API: Next.js, deployed on Vercel
- Database: Supabase (Postgres)
- Price fetchers: Python scripts using crawl4ai (open-source, browser-based scraper) for Amazon, Best Buy, and Walmart
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
- Best Buy: scraper, once a day, low volume, random delays (using scrapers for all three stores for now instead of the official API; can switch Best Buy to the API later once the key comes through)
- Walmart: scraper, once a day, low volume, random delays
- Amazon: scraper, once a day, low volume, random delays

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
- [ ] Create the three tables in Supabase
- [ ] Write a script that imports `products.csv` into `products` and `listings`
- [ ] Verify rows appear in the Supabase dashboard

### Phase 3 — Price fetchers (one file per store, using crawl4ai)
- [ ] `fetch_bestbuy.py` — crawl4ai scraper, updates `listings.current_price` and inserts into `price_history`
- [ ] `fetch_walmart.py` — crawl4ai scraper
- [ ] `fetch_amazon.py` — crawl4ai scraper
- [ ] Each script logs success/failure per product and never crashes the whole run on one bad product

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
