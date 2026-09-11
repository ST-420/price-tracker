import Link from "next/link";
import { searchProducts } from "@/lib/db";
import ProductImage from "@/components/ProductImage";

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  const query = q?.trim() ?? "";
  const results = query.length > 0 ? await searchProducts(query) : [];

  return (
    <div className="min-h-screen" style={{ background: "var(--background)" }}>
      <header
        className="border-b"
        style={{ borderColor: "var(--border)", background: "var(--surface)" }}
      >
        <div className="mx-auto max-w-5xl px-6 py-4">
          <Link href="/" className="flex items-baseline gap-2">
            <span className="text-lg font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>
              Price<span style={{ color: "var(--accent)" }}>Tracker</span>
            </span>
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-10">
        <div className="mb-8">
          <h1 className="text-2xl font-semibold sm:text-3xl" style={{ color: "var(--text-primary)" }}>
            Compare phone &amp; laptop prices
          </h1>
          <p className="mt-1.5 text-sm sm:text-base" style={{ color: "var(--text-secondary)" }}>
            Tracked daily across Amazon, Best Buy, and Walmart.
          </p>
        </div>

        <form action="/" className="flex gap-2">
          <input
            type="text"
            name="q"
            defaultValue={query}
            placeholder="Search a phone or laptop…"
            className="flex-1 rounded-lg border px-4 py-3 text-base outline-none transition-shadow focus:shadow-[0_0_0_3px_var(--accent)]"
            style={{
              borderColor: "var(--border)",
              background: "var(--surface)",
              color: "var(--text-primary)",
            }}
          />
          <button
            type="submit"
            className="rounded-lg px-6 py-3 text-sm font-semibold text-white transition-colors"
            style={{ background: "var(--accent)" }}
          >
            Search
          </button>
        </form>

        <div className="mt-10">
          {query.length === 0 && (
            <div className="rounded-xl border border-dashed px-6 py-16 text-center" style={{ borderColor: "var(--border)" }}>
              <p style={{ color: "var(--text-muted)" }}>Start typing above to search the catalog.</p>
            </div>
          )}

          {query.length > 0 && results.length === 0 && (
            <div className="rounded-xl border border-dashed px-6 py-16 text-center" style={{ borderColor: "var(--border)" }}>
              <p style={{ color: "var(--text-muted)" }}>
                No products matching &ldquo;{query}&rdquo;.
              </p>
            </div>
          )}

          {results.length > 0 && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
              {results.map((product) => (
                <Link
                  key={product.id}
                  href={`/product/${product.id}`}
                  className="group flex flex-col overflow-hidden rounded-xl border transition-shadow hover:shadow-md"
                  style={{ borderColor: "var(--border)", background: "var(--surface)" }}
                >
                  <div
                    className="flex aspect-square items-center justify-center p-4"
                    style={{ background: "var(--surface-raised)" }}
                  >
                    <ProductImage src={product.image_url} alt={product.name} size={140} />
                  </div>
                  <div className="flex flex-1 flex-col gap-1 p-3">
                    <span
                      className="w-fit rounded-full px-2 py-0.5 text-[10px] font-medium capitalize"
                      style={{ background: "var(--surface-raised)", color: "var(--text-muted)" }}
                    >
                      {product.category}
                    </span>
                    <span
                      className="line-clamp-2 text-sm font-medium leading-snug"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {product.name}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
