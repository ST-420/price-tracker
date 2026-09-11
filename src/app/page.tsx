import Link from "next/link";
import { browseCategory, searchProducts } from "@/lib/db";
import ProductCard from "@/components/ProductCard";

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; cat?: string }>;
}) {
  const { q, cat } = await searchParams;
  const query = q?.trim() ?? "";
  const category = cat === "phone" || cat === "laptop" ? cat : null;

  const results = query.length > 0 ? await searchProducts(query) : [];
  const browsed = !query && category ? await browseCategory(category) : [];

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

        {!query && (
          <div className="mt-4 flex gap-2">
            {(["phone", "laptop"] as const).map((c) => (
              <Link
                key={c}
                href={`/?cat=${c}`}
                className="rounded-full border px-3 py-1 text-xs font-medium capitalize transition-colors"
                style={{
                  borderColor: category === c ? "var(--accent)" : "var(--border)",
                  color: category === c ? "var(--accent)" : "var(--text-secondary)",
                  background: "var(--surface)",
                }}
              >
                {c}s
              </Link>
            ))}
          </div>
        )}

        <div className="mt-8">
          {!query && !category && (
            <div className="rounded-xl border border-dashed px-6 py-16 text-center" style={{ borderColor: "var(--border)" }}>
              <p style={{ color: "var(--text-muted)" }}>
                Search above, or browse{" "}
                <Link href="/?cat=phone" className="font-medium underline" style={{ color: "var(--accent)" }}>
                  phones
                </Link>{" "}
                and{" "}
                <Link href="/?cat=laptop" className="font-medium underline" style={{ color: "var(--accent)" }}>
                  laptops
                </Link>
                .
              </p>
            </div>
          )}

          {query.length > 0 && results.length === 0 && (
            <div className="rounded-xl border border-dashed px-6 py-16 text-center" style={{ borderColor: "var(--border)" }}>
              <p style={{ color: "var(--text-muted)" }}>
                No products matching &ldquo;{query}&rdquo;.
              </p>
            </div>
          )}

          {!query && category && browsed.length === 0 && (
            <div className="rounded-xl border border-dashed px-6 py-16 text-center" style={{ borderColor: "var(--border)" }}>
              <p style={{ color: "var(--text-muted)" }}>No {category}s in the catalog yet.</p>
            </div>
          )}

          {(results.length > 0 || browsed.length > 0) && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
              {(query ? results : browsed).map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
