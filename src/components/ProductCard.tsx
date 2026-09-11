import Link from "next/link";
import type { ProductWithPrice } from "@/lib/db";
import ProductImage from "./ProductImage";

export default function ProductCard({ product }: { product: ProductWithPrice }) {
  return (
    <Link
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
      <div className="flex flex-1 flex-col gap-1.5 p-3">
        <div className="flex items-center justify-between gap-2">
          <span
            className="w-fit rounded-full px-2 py-0.5 text-[10px] font-medium capitalize"
            style={{ background: "var(--surface-raised)", color: "var(--text-muted)" }}
          >
            {product.category}
          </span>
          {product.store_count > 1 && (
            <span className="text-[10px] font-medium" style={{ color: "var(--good)" }}>
              {product.store_count} stores
            </span>
          )}
        </div>
        <span className="line-clamp-2 text-sm font-medium leading-snug" style={{ color: "var(--text-primary)" }}>
          {product.name}
        </span>
        {product.lowest_price && (
          <span className="mt-auto pt-1 text-base font-bold" style={{ color: "var(--accent)" }}>
            ${Number(product.lowest_price).toFixed(2)}
          </span>
        )}
      </div>
    </Link>
  );
}
