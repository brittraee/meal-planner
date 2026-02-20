"""Scrape recipes from URLs using recipe-scrapers."""

from __future__ import annotations

import contextlib
import re
from typing import Any

from recipe_scrapers import scrape_me

from src.ingredients import normalize

# Reuse the measure parser from seed script
_QTY_RE = re.compile(
    r"""
    ^\s*
    (\d+\s*/\s*\d+     # fraction like 1/2
    |\d+\.?\d*          # decimal like 2 or 2.5
    )
    \s*(.*)$            # rest is unit
    """,
    re.VERBOSE,
)

_UNIT_ALIASES: dict[str, str] = {
    "tablespoon": "tbsp",
    "tablespoons": "tbsp",
    "teaspoon": "tsp",
    "teaspoons": "tsp",
    "cup": "cup",
    "cups": "cup",
    "ounce": "oz",
    "ounces": "oz",
    "pound": "lb",
    "pounds": "lb",
    "gram": "g",
    "grams": "g",
    "kilogram": "kg",
    "kilograms": "kg",
    "ml": "ml",
    "liter": "L",
    "liters": "L",
    "clove": "clove",
    "cloves": "clove",
    "can": "can",
    "cans": "can",
}


def _parse_qty_unit(text: str) -> tuple[float | None, str | None]:
    """Parse quantity and unit from an ingredient string prefix."""
    match = _QTY_RE.match(text.strip())
    if not match:
        return None, None

    raw_qty, raw_unit = match.group(1).strip(), match.group(2).strip()

    if "/" in raw_qty:
        num, denom = raw_qty.split("/")
        qty = float(num.strip()) / float(denom.strip())
    else:
        qty = float(raw_qty)

    unit_lower = raw_unit.lower().rstrip(".")
    # Check full string first, then first word only (e.g. "cups flour" → "cups" → "cup")
    if unit_lower in _UNIT_ALIASES:
        return qty, _UNIT_ALIASES[unit_lower]
    first_word = unit_lower.split()[0] if unit_lower else ""
    if first_word in _UNIT_ALIASES:
        return qty, _UNIT_ALIASES[first_word]
    return qty, unit_lower if unit_lower else None


def _slugify(title: str) -> str:
    """Convert a recipe title to a URL-safe slug ID."""
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return f"url_{slug}"


def scrape_recipe(url: str) -> dict[str, Any]:
    """Scrape a recipe URL and return a structured dict.

    Returns a dict matching the insert_recipe_dict() format:
        id, title, protein, servings, source_url, source_type,
        instructions, image_url, ingredients (list), tags (list).

    Raises:
        Exception: If the URL cannot be scraped.
    """
    scraper = scrape_me(url)

    title = scraper.title()
    recipe_id = _slugify(title)

    # Parse ingredients
    ingredients = []
    for line in scraper.ingredients():
        qty, unit = _parse_qty_unit(line)
        normalized = normalize(line)
        ingredients.append(
            {
                "raw_text": line,
                "normalized_name": normalized,
                "is_optional": False,
                "qty": qty,
                "unit": unit,
            }
        )

    # Build tags from category if available
    tags = []
    try:
        cat = scraper.category()
        if cat:
            tags.extend(t.strip().lower() for t in cat.split(",") if t.strip())
    except (AttributeError, NotImplementedError):
        pass

    # Get servings as int
    servings = 4
    try:
        raw_yields = scraper.yields()
        if raw_yields:
            nums = re.findall(r"\d+", raw_yields)
            if nums:
                servings = int(nums[0])
    except (AttributeError, NotImplementedError):
        pass

    # Get image
    image_url = ""
    with contextlib.suppress(AttributeError, NotImplementedError):
        image_url = scraper.image() or ""

    # Get instructions
    instructions = ""
    with contextlib.suppress(AttributeError, NotImplementedError):
        instructions = scraper.instructions() or ""

    return {
        "id": recipe_id,
        "title": title,
        "protein": "unknown",
        "prep_notes": "",
        "servings": servings,
        "source_url": url,
        "source_type": "url",
        "instructions": instructions,
        "image_url": image_url,
        "ingredients": ingredients,
        "tags": tags,
    }
