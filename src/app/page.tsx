import Link from "next/link";
import { searchProducts } from "@/lib/db";

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  const query = q?.trim() ?? "";
  const results = query.length > 0 ? await searchProducts(query) : [];

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black">
      <main className="mx-auto max-w-2xl px-6 py-16">
        <h1 className="text-2xl font-semibold text-black dark:text-zinc-50">
          Price Tracker
        </h1>
        <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
          Search a phone or laptop to compare prices across Amazon, Best Buy, and Walmart.
        </p>

        <form action="/" className="mt-8 flex gap-2">
          <input
            type="text"
            name="q"
            defaultValue={query}
            placeholder="e.g. iPhone 15, MacBook Air, Galaxy S24"
            className="flex-1 rounded-md border border-zinc-300 bg-white px-4 py-2 text-black outline-none focus:border-zinc-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
          />
          <button
            type="submit"
            className="rounded-md bg-black px-5 py-2 text-white hover:bg-zinc-800 dark:bg-white dark:text-black dark:hover:bg-zinc-200"
          >
            Search
          </button>
        </form>

        <div className="mt-8">
          {query.length === 0 && (
            <p className="text-sm text-zinc-500 dark:text-zinc-500">
              Start typing above to search the catalog.
            </p>
          )}

          {query.length > 0 && results.length === 0 && (
            <p className="text-sm text-zinc-500 dark:text-zinc-500">
              No products matching &ldquo;{query}&rdquo;.
            </p>
          )}

          <ul className="flex flex-col gap-2">
            {results.map((product) => (
              <li key={product.id}>
                <Link
                  href={`/product/${product.id}`}
                  className="block rounded-md border border-zinc-200 bg-white px-4 py-3 hover:border-zinc-400 dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-zinc-600"
                >
                  <div className="font-medium text-black dark:text-zinc-50">
                    {product.name}
                  </div>
                  <div className="text-sm text-zinc-500 dark:text-zinc-500 capitalize">
                    {product.category}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </main>
    </div>
  );
}
