"""Search terms used to discover phones and laptops on each store, plus the
soft cap on total catalog size (see price tracker.md > Scope)."""

CATALOG_CAP = 500

SEARCH_QUERIES = {
    "phone": [
        "iphone 15",
        "iphone 16",
        "samsung galaxy s24",
        "samsung galaxy s25",
        "samsung galaxy a15",
        "google pixel 9",
        "google pixel 8",
        "motorola edge",
        "oneplus 12",
        "iphone se",
    ],
    "laptop": [
        "macbook air",
        "macbook pro",
        "dell xps 13",
        "dell inspiron laptop",
        "hp pavilion laptop",
        "lenovo thinkpad",
        "asus zenbook",
        "acer aspire laptop",
        "microsoft surface laptop",
        "chromebook",
    ],
}
