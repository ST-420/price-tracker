import Link from "next/link";
import { notFound } from "next/navigation";
import { getListings, getPriceHistory, getProduct } from "@/lib/db";
import PriceChart from "@/components/PriceChart";

const STORE_LABELS: Record<string, string> = {
  amazon: "Amazon",
  bestbuy: "Best Buy",
  walmart: "Walmart",
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

  const [listings, history] = await Promise.all([
    getListings(productId),
    getPriceHistory(productId),
  ]);

  const cheapestPrice = listings.reduce<number | null>((min, l) => {
    const price = l.current_price ? Number(l.current_price) : null;
    if (price === null) return min;
    return min === null || price < min ? price : min;
  }, null);

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black">
      <main className="mx-auto max-w-2xl px-6 py-16">
        <Link href="/" className="text-sm text-zinc-500 hover:underline dark:text-zinc-500">
          ← Back to search
        </Link>

        <h1 className="mt-3 text-2xl font-semibold text-black dark:text-zinc-50">
          {product.name}
        </h1>
        <p className="mt-1 text-sm capitalize text-zinc-500 dark:text-zinc-500">
          {product.category}
        </p>

        <div className="mt-8">
          <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-500">
            Compare prices
          </h2>
          {listings.length === 0 ? (
            <p className="text-sm text-zinc-500 dark:text-zinc-500">
              No verified cross-store listing yet for this product.
            </p>
          ) : (
            <table className="w-full overflow-hidden rounded-md border border-zinc-200 text-left dark:border-zinc-800">
              <tbody>
                {listings.map((listing) => {
                  const price = listing.current_price ? Number(listing.current_price) : null;
                  const isCheapest = price !== null && price === cheapestPrice;
                  return (
                    <tr
                      key={listing.id}
                      className={`border-b border-zinc-200 last:border-b-0 dark:border-zinc-800 ${
                        isCheapest ? "bg-green-50 dark:bg-green-950/30" : "bg-white dark:bg-zinc-900"
                      }`}
                    >
                      <td className="px-4 py-3 font-medium text-black dark:text-zinc-50">
                        {STORE_LABELS[listing.store] ?? listing.store}
                        {isCheapest && (
                          <span className="ml-2 rounded-full bg-green-600 px-2 py-0.5 text-xs font-normal text-white">
                            Cheapest
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right text-black dark:text-zinc-50">
                        {price !== null ? `$${price.toFixed(2)}` : "—"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <a
                          href={listing.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-blue-600 hover:underline dark:text-blue-400"
                        >
                          View →
                        </a>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        <div className="mt-10">
          <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-500">
            Price history
          </h2>
          <PriceChart history={history} />
        </div>
      </main>
    </div>
  );
}
