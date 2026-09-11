"use client";

import { useMemo, useState } from "react";
import type { PricePoint } from "@/lib/db";

const STORE_LABELS: Record<string, string> = {
  amazon: "Amazon",
  bestbuy: "Best Buy",
  walmart: "Walmart",
};

// First three slots of the dataviz skill's validated categorical palette —
// these three specifically pass the stricter "all-pairs" check (not just
// adjacent-pair), which matters here since a viewer compares all 3 lines
// against each other, not just neighbors in a fixed order.
const STORE_COLORS: Record<string, { light: string; dark: string }> = {
  amazon: { light: "#2a78d6", dark: "#3987e5" }, // blue
  bestbuy: { light: "#eb6834", dark: "#d95926" }, // orange
  walmart: { light: "#1baf7a", dark: "#199e70" }, // aqua
};

const WIDTH = 600;
const HEIGHT = 260;
// Right padding leaves room for the end-of-line price label so it never gets
// clipped by the SVG's own edge.
const PADDING = { top: 16, right: 56, bottom: 28, left: 56 };

export default function PriceChart({ history }: { history: PricePoint[] }) {
  const [hoverX, setHoverX] = useState<number | null>(null);

  const series = useMemo(() => {
    const byStore = new Map<string, { x: number; y: number; price: number }[]>();
    for (const store of new Set(history.map((h) => h.store))) {
      byStore.set(store, []);
    }
    const times = history.map((h) => new Date(h.recorded_at).getTime());
    const prices = history.map((h) => Number(h.price));
    const minTime = Math.min(...times);
    const maxTime = Math.max(...times);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const timeRange = maxTime - minTime || 1;
    const priceRange = maxPrice - minPrice || 1;

    const innerW = WIDTH - PADDING.left - PADDING.right;
    const innerH = HEIGHT - PADDING.top - PADDING.bottom;

    for (const point of history) {
      const t = new Date(point.recorded_at).getTime();
      const price = Number(point.price);
      const x = PADDING.left + ((t - minTime) / timeRange) * innerW;
      const y = PADDING.top + innerH - ((price - minPrice) / priceRange) * innerH;
      byStore.get(point.store)?.push({ x, y, price });
    }
    for (const points of byStore.values()) points.sort((a, b) => a.x - b.x);

    return { byStore, minPrice, maxPrice };
  }, [history]);

  if (history.length === 0) {
    return (
      <p className="text-sm" style={{ color: "var(--text-muted)" }}>
        No price history yet — check back after the daily price check has run a few times.
      </p>
    );
  }

  const stores = Array.from(series.byStore.keys());
  const gridSteps = series.minPrice === series.maxPrice ? [0.5] : [0, 0.5, 1];

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-4">
        {stores.map((store) => (
          <div key={store} className="flex items-center gap-1.5 text-sm">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: STORE_COLORS[store]?.light ?? "#888" }}
            />
            <span style={{ color: "var(--text-secondary)" }}>
              {STORE_LABELS[store] ?? store}
            </span>
          </div>
        ))}
      </div>

      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="w-full"
        onMouseMove={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const x = ((e.clientX - rect.left) / rect.width) * WIDTH;
          setHoverX(x);
        }}
        onMouseLeave={() => setHoverX(null)}
      >
        {/* gridlines */}
        {gridSteps.map((t) => {
          const y = PADDING.top + t * (HEIGHT - PADDING.top - PADDING.bottom);
          const price = series.maxPrice - t * (series.maxPrice - series.minPrice);
          return (
            <g key={t}>
              <line
                x1={PADDING.left}
                x2={WIDTH - PADDING.right}
                y1={y}
                y2={y}
                stroke="var(--border)"
                strokeWidth={1}
              />
              <text
                x={PADDING.left - 8}
                y={y}
                textAnchor="end"
                dominantBaseline="middle"
                fill="var(--text-muted)"
                fontSize={10}
              >
                ${price.toFixed(0)}
              </text>
            </g>
          );
        })}

        {stores.map((store) => {
          const points = series.byStore.get(store) ?? [];
          if (points.length === 0) return null;
          const path = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
          const last = points[points.length - 1];
          const color = STORE_COLORS[store]?.light ?? "#888";
          return (
            <g key={store}>
              <path d={path} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
              {/* end marker, with a surface ring so it stays legible over the line */}
              <circle cx={last.x} cy={last.y} r={5} fill={color} stroke="var(--surface)" strokeWidth={2} />
              <text x={last.x + 8} y={last.y} dominantBaseline="middle" fontSize={11} fontWeight={500} fill="var(--text-secondary)">
                ${last.price.toFixed(0)}
              </text>
            </g>
          );
        })}

        {hoverX !== null && (
          <line
            x1={hoverX}
            x2={hoverX}
            y1={PADDING.top}
            y2={HEIGHT - PADDING.bottom}
            stroke="var(--text-muted)"
            strokeWidth={1}
          />
        )}
      </svg>
    </div>
  );
}
