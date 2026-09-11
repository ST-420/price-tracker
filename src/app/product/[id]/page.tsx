import Link from "next/link";
import { notFound } from "next/navigation";
import { getListings, getPriceHistory, getPriceStats, getProduct } from "@/lib/db";
import PriceChart from "@/components/PriceChart";
import ProductImage from "@/components/ProductImage";

const STORE_META: Record<string, { label: string; color: string }> = {
  amazon: { label: "Amazon", color: "#2a78d6" },
  bestbuy: { label: "Best Buy", color: "#eb6834" },
  walmart: { label: "Walmart", color: "#1baf7a" },
};

export default async function ProductPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const productId = Number(id);
  if (!Number.isInteger(productId)) notFound();

  const product = await getProduct(productId);
  if (!product) notFound();

  const [listings, history, stats] = await Promise.all([
    getListings(productId),
    getPriceHistory(productId),
    getPriceStats(productId),
  ]);

  const cheapestPrice = listings.reduce<number | null>((min, l) => {
    const price = l.current_price ? Number(l.current_price) : null;
    if (price === null) return min;
    return min === null || price < min ? price : min;
  }, null);

  return (
    <div className="min-h-screen" style={{ background: "var(--background)" }}>
      <header className="border-b" style={{ borderColor: "var(--border)", background: "var(--surface)" }}>
        <div className="mx-auto max-w-5xl px-6 py-4">
          <Link href="/" className="flex items-baseline gap-2">
            <span className="text-lg font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>
              Price<span style={{ color: "var(--accent)" }}>Tracker</span>
            </span>
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-10">
        <Link
          href="/"
          className="mb-6 inline-block text-sm hover:underline"
          style={{ color: "var(--text-muted)" }}
        >
          ← Back to search
        </Link>

        <div
          className="flex flex-col gap-6 rounded-xl border p-6 sm:flex-row sm:items-center"
          style={{ borderColor: "var(--border)", background: "var(--surface)" }}
        >
          <div
            className="flex aspect-square w-full shrink-0 items-center justify-center rounded-lg p-6 sm:w-48"
            style={{ background: "var(--surface-raised)" }}
          >
            <ProductImage src={product.image_url} alt={product.name} size={160} />
          </div>
          <div>
            <span
              className="w-fit rounded-full px-2 py-0.5 text-xs font-medium capitalize"
              style={{ background: "var(--surface-raised)", color: "var(--text-muted)" }}
            >
              {product.category}
            </span>
            <h1 className="mt-2 text-xl font-semibold leading-snug sm:text-2xl" style={{ color: "var(--text-primary)" }}>
              {product.name}
            </h1>
            {cheapestPrice !== null && (
              <p className="mt-3 text-3xl font-bold" style={{ color: "var(--accent)" }}>
                ${cheapestPrice.toFixed(2)}
                <span className="ml-2 text-sm font-normal" style={{ color: "var(--text-muted)" }}>
                  lowest price now
                </span>
              </p>
            )}
          </div>
        </div>

        {stats && (
          <div className="mt-6 grid grid-cols-3 gap-4">
            <StatTile label="Lowest ever" value={stats.lowest} />
            <StatTile label="Average" value={stats.average} />
            <StatTile label="Highest ever" value={stats.highest} />
          </div>
        )}

        <section className="mt-10">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
            Compare prices
          </h2>
          {listings.length === 0 ? (
            <div className="rounded-xl border border-dashed px-6 py-10 text-center" style={{ borderColor: "var(--border)" }}>
              <p style={{ color: "var(--text-muted)" }}>
                No verified cross-store listing yet for this product.
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {listings.map((listing) => {
                const price = listing.current_price ? Number(listing.current_price) : null;
                const isCheapest = price !== null && price === cheapestPrice;
                const meta = STORE_META[listing.store] ?? { label: listing.store, color: "#888" };
                return (
                  <a
                    key={listing.id}
                    href={listing.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-4 rounded-xl border p-4 transition-shadow hover:shadow-md"
                    style={{
                      borderColor: isCheapest ? "var(--good)" : "var(--border)",
                      background: isCheapest ? "var(--good-bg)" : "var(--surface)",
                    }}
                  >
                    <span
                      className="h-2.5 w-2.5 shrink-0 rounded-full"
                      style={{ background: meta.color }}
                    />
                    <span className="flex-1 font-medium" style={{ color: "var(--text-primary)" }}>
                      {meta.label}
                    </span>
                    {isCheapest && (
                      <span
                        className="rounded-full px-2.5 py-1 text-xs font-semibold text-white"
                        style={{ background: "var(--good)" }}
                      >
                        Cheapest
                      </span>
                    )}
                    <span className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>
                      {price !== null ? `$${price.toFixed(2)}` : "—"}
                    </span>
                    <span style={{ color: "var(--text-muted)" }}>→</span>
                  </a>
                );
              })}
            </div>
          )}
        </section>

        <section className="mt-10">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
            Price history
          </h2>
          <div className="rounded-xl border p-5" style={{ borderColor: "var(--border)", background: "var(--surface)" }}>
            <PriceChart history={history} />
          </div>
        </section>
      </main>
    </div>
  );
}

function StatTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border p-4 text-center" style={{ borderColor: "var(--border)", background: "var(--surface)" }}>
      <div className="text-lg font-semibold sm:text-xl" style={{ color: "var(--text-primary)" }}>
        ${value.toFixed(2)}
      </div>
      <div className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>
        {label}
      </div>
    </div>
  );
}
