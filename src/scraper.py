"""Scrape recipes from URLs using recipe-scrapers."""

from __future__ import annotations

import contextlib
import re
from fractions import Fraction
from typing import Any

import requests
from recipe_scrapers import scrape_html

from src.ingredients import normalize

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_UNIT_ALIASES: dict[str, str] = {
    "tablespoon": "tbsp",
    "tablespoons": "tbsp",
    "tbsp": "tbsp",
    "teaspoon": "tsp",
    "teaspoons": "tsp",
    "tsp": "tsp",
    "cup": "cup",
    "cups": "cup",
    "ounce": "oz",
    "ounces": "oz",
    "oz": "oz",
    "pound": "lb",
    "pounds": "lb",
    "lb": "lb",
    "lbs": "lb",
    "gram": "g",
    "grams": "g",
    "g": "g",
    "kilogram": "kg",
    "kilograms": "kg",
    "kg": "kg",
    "ml": "ml",
    "milliliter": "ml",
    "milliliters": "ml",
    "liter": "L",
    "liters": "L",
    "clove": "clove",
    "cloves": "clove",
    "can": "can",
    "cans": "can",
    "bunch": "bunch",
    "bunches": "bunch",
    "head": "head",
    "heads": "head",
    "stalk": "stalk",
    "stalks": "stalk",
    "sprig": "sprig",
    "sprigs": "sprig",
    "slice": "slice",
    "slices": "slice",
    "piece": "piece",
    "pieces": "piece",
    "pinch": "pinch",
    "dash": "dash",
    "package": "package",
    "packages": "package",
    "jar": "jar",
    "jars": "jar",
    "bag": "bag",
    "bags": "bag",
}

# Size words between qty and ingredient name (not units)
_SKIP_WORDS = {"large", "medium", "small", "whole", "extra", "thin", "thick"}

# Descriptors to strip from ingredient names
_DESCRIPTOR_RE = re.compile(
    r"\b("
    r"boneless|skinless|chopped|diced|minced|sliced|shredded|grated|"
    r"melted|softened|crushed|torn|peeled|seeded|trimmed|halved|"
    r"quartered|cubed|julienned|thinly|roughly|finely|coarsely|"
    r"freshly|lightly|well|very|about|approximately"
    r")\b",
    re.IGNORECASE,
)

# Matches a number: integer, decimal, fraction, or mixed fraction
_NUM_RE = re.compile(r"(\d+\s+\d+/\d+|\d+/\d+|\d+\.?\d*)")

# Matches "X to Y" or "X-Y" ranges at the start (handles mixed fractions)
_RANGE_RE = re.compile(
    r"^(\d+(?:\s+\d+/\d+)?(?:/\d+)?)\s+(?:to|-)\s+(\d+(?:\s+\d+/\d+)?(?:/\d+)?)\s+(.*)",
    re.IGNORECASE,
)


def _parse_num(text: str) -> float:
    """Parse a number string (integer, decimal, fraction, or mixed fraction)."""
    text = text.strip()
    if " " in text:
        parts = text.split(None, 1)
        return float(parts[0]) + float(Fraction(parts[1]))
    if "/" in text:
        return float(Fraction(text))
    return float(text)


def _clean_name(name: str) -> str:
    """Strip descriptors and parentheticals from an ingredient name."""
    name = re.sub(r"\([^)]*\)", "", name)
    name = _DESCRIPTOR_RE.sub(" ", name)
    name = re.sub(r"\s*,\s*$", "", name)
    name = re.sub(r"^,\s*", "", name)
    return " ".join(name.split()).strip(" ,;-")


def parse_ingredient_line(line: str) -> tuple[float | None, str | None, str]:
    """Parse a full ingredient line into (qty, unit, name).

    Handles mixed fractions (1 1/2), ranges (1 to 2), unit aliases,
    size words (large, medium), and descriptor stripping.
    """
    text = line.strip()

    # Try range pattern first: "1 to 2 cups flour"
    range_match = _RANGE_RE.match(text)
    if range_match:
        try:
            q1 = _parse_num(range_match.group(1))
            q2 = _parse_num(range_match.group(2))
            qty = (q1 + q2) / 2
            rest = range_match.group(3).strip()
            words = rest.split(None, 1)
            if words and words[0].lower().rstrip(".") in _UNIT_ALIASES:
                unit = _UNIT_ALIASES[words[0].lower().rstrip(".")]
                name = _clean_name(words[1] if len(words) > 1 else "")
            else:
                unit = None
                name = _clean_name(rest)
            return qty, unit, normalize(name) if name else normalize(rest)
        except (ValueError, ZeroDivisionError):
            pass

    # Standard: try to match a number at the start
    match = _NUM_RE.match(text)
    if match:
        try:
            qty = _parse_num(match.group(1))
        except (ValueError, ZeroDivisionError):
            return None, None, normalize(_clean_name(text))

        rest = text[match.end():].strip()

        # Strip parentheticals before unit detection: "1 (15 oz) can" → "1 can"
        rest = re.sub(r"\([^)]*\)", "", rest).strip()

        # Check if rest starts with another fraction (mixed: "1 1/2")
        match2 = re.match(r"^(\d+/\d+)\s*(.*)", rest)
        if match2:
            try:
                qty += float(Fraction(match2.group(1)))
                rest = match2.group(2).strip()
            except (ValueError, ZeroDivisionError):
                pass

        # Check for unit
        words = rest.split(None, 1)
        if words:
            first = words[0].lower().rstrip(".,")
            if first in _UNIT_ALIASES:
                unit = _UNIT_ALIASES[first]
                name = _clean_name(words[1] if len(words) > 1 else "")
            elif first in _SKIP_WORDS:
                unit = None
                name = _clean_name(words[1] if len(words) > 1 else "")
            else:
                unit = None
                name = _clean_name(rest)
        else:
            unit = None
            name = ""

        return qty, unit, normalize(name) if name else ""

    return None, None, normalize(_clean_name(text))


def _slugify(title: str) -> str:
    """Convert a recipe title to a URL-safe slug ID."""
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return f"url_{slug}"


def _fetch_html(url: str) -> str:
    """Fetch HTML from a URL with a browser-like user agent."""
    resp = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=15)
    resp.raise_for_status()
    return resp.text


def scrape_recipe(url: str) -> dict[str, Any]:
    """Scrape a recipe URL and return a structured dict.

    Returns a dict matching the insert_recipe_dict() format:
        id, title, protein, servings, source_url, source_type,
        instructions, image_url, ingredients (list), tags (list).

    Raises:
        Exception: If the URL cannot be scraped.
    """
    html = _fetch_html(url)
    scraper = scrape_html(html, org_url=url)

    title = scraper.title()
    recipe_id = _slugify(title)

    # Parse ingredients with proper qty/unit/name extraction
    ingredients = []
    for line in scraper.ingredients():
        qty, unit, name = parse_ingredient_line(line)
        ingredients.append(
            {
                "raw_text": line,
                "normalized_name": name,
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
