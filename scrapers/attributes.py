"""Parses brand, model name, storage, RAM, screen size, and color out of a
scraped listing title. Used for rule-3 ("attribute") matching in db.py, and
as a fallback when a store doesn't expose a clean UPC/model number.

This is inherently heuristic — real titles are unstructured marketing copy
that varies a lot between stores. The matching rule this feeds is strict
(brand + model name + storage must ALL match exactly, storage/RAM mismatch
is a hard reject), so a parsing miss just means two real listings stay
unlinked rather than getting wrongly paired — safe by design.
"""

import re

KNOWN_BRANDS = [
    "Apple", "Samsung", "Google", "Motorola", "OnePlus",
    "Dell", "HP", "Lenovo", "Asus", "Acer", "Microsoft",
]

COLOR_WORDS = [
    "space gray", "space black", "rose gold", "deep forest", "sky blue",
    "natural titanium", "blue titanium", "black titanium", "white titanium",
    "desert titanium", "midnight", "starlight", "graphite", "obsidian",
    "charcoal", "titanium", "platinum", "silver", "gold", "black", "white",
    "blue", "red", "green", "purple", "pink", "gray", "grey", "navy",
    "coral", "mint", "lavender", "cream", "sand", "sage",
]

NOISE_WORDS = [
    "unlocked", "factory unlocked", "fully unlocked", "renewed", "refurbished",
    "5g", "4g", "lte", "smartphone", "cell phone", "dual-sim", "dual sim",
    "international model", "new", "version", "windows 11", "win 11",
    "laptop", "business laptop", "business pc",
]


def extract_brand(title: str, hint: str | None = None) -> str | None:
    lower = title.lower()
    for brand in KNOWN_BRANDS:
        if brand.lower() in lower:
            return brand
    # Some listings (e.g. Amazon's Samsung phones) never say the brand in the
    # title at all. Fall back to a hint — e.g. the search term that found it
    # often starts with the brand ("samsung galaxy s24").
    if hint:
        hint_lower = hint.lower()
        for brand in KNOWN_BRANDS:
            if brand.lower() in hint_lower:
                return brand
    return None


def _gb_matches(title: str):
    """Returns list of (start, end, value_in_gb, raw_text, context) for every
    <number><GB|TB> occurrence in the title. `context` is the surrounding
    comma/pipe/colon-delimited clause (e.g. "8GB DDR5" or "512GB SSD"), not a
    fixed character window — a fixed window bleeds into a neighboring clause
    when specs are packed close together (e.g. "8GB DDR5, 512GB SSD"), which
    would otherwise misclassify both numbers as the same kind of spec."""
    matches = []
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(GB|TB)\b", title, re.IGNORECASE):
        value = float(m.group(1))
        if m.group(2).upper() == "TB":
            value *= 1024
        DELIMS = ",|:;-"
        clause_start = max(title.rfind(sep, 0, m.start()) for sep in DELIMS) + 1
        clause_end_candidates = [title.find(sep, m.end()) for sep in DELIMS]
        clause_end_candidates = [c for c in clause_end_candidates if c != -1]
        clause_end = min(clause_end_candidates) if clause_end_candidates else len(title)
        context = title[clause_start:clause_end].lower()
        matches.append((m.start(), m.end(), value, m.group(0), context))
    return matches


def extract_ram(title: str) -> str | None:
    for start, end, value, raw, context in _gb_matches(title):
        if any(kw in context for kw in ("ram", "memory", "ddr")):
            return f"{int(value)}GB"
    return None


def extract_storage(title: str) -> str | None:
    gb_matches = _gb_matches(title)
    ram_spans = set()
    for start, end, value, raw, context in gb_matches:
        if any(kw in context for kw in ("ram", "memory", "ddr")):
            ram_spans.add((start, end))

    # Prefer an explicitly-labeled storage figure.
    for start, end, value, raw, context in gb_matches:
        if (start, end) in ram_spans:
            continue
        if any(kw in context for kw in ("ssd", "storage", "rom", "hard drive", "emmc")):
            return f"{int(value)}GB" if value < 1024 else f"{int(value / 1024)}TB"

    # Otherwise, the largest unlabeled figure that isn't RAM.
    candidates = [(v, raw) for s, e, v, raw, c in gb_matches if (s, e) not in ram_spans]
    if candidates:
        value = max(v for v, _ in candidates)
        return f"{int(value)}GB" if value < 1024 else f"{int(value / 1024)}TB"
    return None


def extract_screen_size(title: str) -> str | None:
    m = re.search(r'(\d+(?:\.\d+)?)[\s-]*(?:"|inch|inches|″)', title, re.IGNORECASE)
    return f'{m.group(1)}"' if m else None


def extract_color(title: str) -> str | None:
    lower = title.lower()
    for color in COLOR_WORDS:  # longest/most-specific entries first, as listed
        if color in lower:
            return color.title()
    return None


def extract_model_name(title: str, brand: str | None) -> str:
    """Best-effort "core" product name, stripped of brand, storage/RAM/screen
    figures, color, and common marketing noise words."""
    core = title

    # Prefer the segment before the first comma (common on Amazon), else the
    # first " - "-delimited segment after the brand (common on Best Buy).
    if "," in core:
        core = core.split(",")[0]
    elif " - " in core:
        parts = [p.strip() for p in core.split(" - ")]
        core = parts[1] if len(parts) > 1 else parts[0]

    if brand:
        core = re.sub(re.escape(brand), "", core, flags=re.IGNORECASE)

    for _, _, _, raw, _ in _gb_matches(core):
        core = core.replace(raw, "")

    size = extract_screen_size(core)
    if size:
        core = re.sub(r'\d+(?:\.\d+)?[\s-]*(?:"|inch|inches|″)', "", core, flags=re.IGNORECASE)

    for color in COLOR_WORDS:
        core = re.sub(re.escape(color), "", core, flags=re.IGNORECASE)

    for word in NOISE_WORDS:
        core = re.sub(r"\b" + re.escape(word) + r"\b", "", core, flags=re.IGNORECASE)

    core = re.sub(r"\([^)]*\)", " ", core)  # parenthetical asides
    core = re.sub(r"[|:;,-]+", " ", core)
    core = re.sub(r"\s+", " ", core).strip()
    return core


def normalize_model_number(raw: str) -> str:
    return re.sub(r"[\s-]", "", raw).upper()


def parse(title: str, brand_hint: str | None = None) -> dict:
    brand = extract_brand(title, hint=brand_hint)
    return {
        "brand": brand,
        "model_name": extract_model_name(title, brand),
        "storage": extract_storage(title),
        "ram": extract_ram(title),
        "screen_size": extract_screen_size(title),
        "color": extract_color(title),
    }
