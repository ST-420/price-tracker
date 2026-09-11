"use client";

import { useState } from "react";

// Product photos come from whichever store's CDN scraped them (varies per
// product), so this uses a plain <img> rather than next/image (which would
// need every possible CDN host allow-listed in next.config.ts). Falls back
// to a simple placeholder icon if there's no image, or the hotlinked one
// fails to load.
export default function ProductImage({
  src,
  alt,
  size = 120,
}: {
  src: string | null;
  alt: string;
  size?: number;
}) {
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    return (
      <svg
        width={size * 0.5}
        height={size * 0.5}
        viewBox="0 0 24 24"
        fill="none"
        stroke="var(--text-muted)"
        strokeWidth={1.5}
        aria-label="No image available"
      >
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <circle cx="9" cy="9" r="2" />
        <path d="M21 15l-5-5L5 21" />
      </svg>
    );
  }

  // eslint-disable-next-line @next/next/no-img-element
  return (
    <img
      src={src}
      alt={alt}
      style={{ maxWidth: size, maxHeight: size, width: "auto", height: "auto" }}
      className="object-contain"
      onError={() => setFailed(true)}
    />
  );
}
