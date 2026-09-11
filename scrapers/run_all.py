"""Runs the Amazon, Best Buy, and Walmart scrapers one after another. If one
store's scraper crashes outright, the others still run — this is the script
the daily GitHub Actions job (Phase 4) will call."""

import asyncio

from . import amazon, bestbuy, walmart

STORES = [amazon, bestbuy, walmart]


async def main():
    for store_module in STORES:
        try:
            await store_module.run()
        except Exception as e:
            print(f"[{store_module.STORE}] CRASHED: {e}")


if __name__ == "__main__":
    asyncio.run(main())
