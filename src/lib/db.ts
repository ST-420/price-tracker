// Shared Postgres connection pool (Supabase). Server-only — this file is
// never bundled for the browser because it's only imported from Server
// Components and Route Handlers, which run in Node.js.
import { Pool } from "pg";

// A plain global (not module-level) survives Next.js dev-server hot reloads,
// which otherwise re-run this module and leak a new pool on every edit.
const globalForDb = globalThis as unknown as { pgPool?: Pool };

export const pool =
  globalForDb.pgPool ??
  new Pool({
    connectionString: process.env.SUPABASE_DB_URL,
    max: 5,
  });

if (process.env.NODE_ENV !== "production") {
  globalForDb.pgPool = pool;
}

export type Listing = {
  id: number;
  store: "amazon" | "bestbuy" | "walmart";
  url: string;
  current_price: string | null;
  in_stock: boolean | null;
  last_checked: string | null;
};

export type Product = {
  id: number;
  brand: string;
  model: string;
  category: "phone" | "laptop";
  name: string;
  image_url: string | null;
};

export type ProductWithPrice = Product & {
  lowest_price: string | null;
  store_count: number;
};

export type PricePoint = {
  store: string;
  price: string;
  recorded_at: string;
};

export async function searchProducts(query: string): Promise<ProductWithPrice[]> {
  const { rows } = await pool.query<ProductWithPrice>(
    `SELECT p.id, p.brand, p.model, p.category, p.name, p.image_url,
            min(l.current_price) AS lowest_price,
            count(l.id) AS store_count
     FROM products p
     JOIN listings l ON l.product_id = p.id
     WHERE p.name ILIKE $1
     GROUP BY p.id
     ORDER BY p.name
     LIMIT 30;`,
    [`%${query}%`]
  );
  return rows;
}

export async function browseCategory(category: "phone" | "laptop"): Promise<ProductWithPrice[]> {
  const { rows } = await pool.query<ProductWithPrice>(
    `SELECT p.id, p.brand, p.model, p.category, p.name, p.image_url,
            min(l.current_price) AS lowest_price,
            count(l.id) AS store_count
     FROM products p
     JOIN listings l ON l.product_id = p.id
     WHERE p.category = $1
     GROUP BY p.id
     ORDER BY count(l.id) DESC, p.name
     LIMIT 12;`,
    [category]
  );
  return rows;
}

export async function getProduct(id: number): Promise<Product | null> {
  const { rows } = await pool.query<Product>(
    `SELECT id, brand, model, category, name, image_url FROM products WHERE id = $1;`,
    [id]
  );
  return rows[0] ?? null;
}

// Only listings that were confidently cross-store matched (match_method set
// by one of the three matching rules — see price tracker.md > Scope) are
// shown on the comparison page, per project rules. An unmatched listing
// still exists in the database (its own unlinked product), it just isn't
// surfaced here as part of a price comparison.
export async function getListings(productId: number): Promise<Listing[]> {
  const { rows } = await pool.query<Listing>(
    `SELECT id, store, url, current_price, in_stock, last_checked
     FROM listings WHERE product_id = $1 AND match_method IS NOT NULL ORDER BY store;`,
    [productId]
  );
  return rows;
}

export async function getPriceHistory(productId: number): Promise<PricePoint[]> {
  const { rows } = await pool.query<PricePoint>(
    `SELECT l.store, ph.price, ph.recorded_at
     FROM price_history ph
     JOIN listings l ON l.id = ph.listing_id
     WHERE l.product_id = $1
     ORDER BY ph.recorded_at ASC;`,
    [productId]
  );
  return rows;
}

export type PriceStats = { lowest: number; highest: number; average: number } | null;

export async function getPriceStats(productId: number): Promise<PriceStats> {
  const { rows } = await pool.query<{ lowest: string; highest: string; average: string }>(
    `SELECT min(ph.price) AS lowest, max(ph.price) AS highest, avg(ph.price) AS average
     FROM price_history ph
     JOIN listings l ON l.id = ph.listing_id
     WHERE l.product_id = $1;`,
    [productId]
  );
  const row = rows[0];
  if (!row || row.lowest === null) return null;
  return { lowest: Number(row.lowest), highest: Number(row.highest), average: Number(row.average) };
}
