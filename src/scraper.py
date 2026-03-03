"""Scrape recipes from URLs using recipe-scrapers."""

from __future__ import annotations

import contextlib
import re
from fractions import Fraction
from typing import Any

import cloudscraper
from recipe_scrapers import scrape_html

from src.ingredients import normalize

# Unicode fraction characters → ASCII equivalents
_UNICODE_FRACTIONS: dict[str, str] = {
    "\u00bd": "1/2",  # ½
    "\u00bc": "1/4",  # ¼
    "\u00be": "3/4",  # ¾
    "\u2153": "1/3",  # ⅓
    "\u2154": "2/3",  # ⅔
    "\u2155": "1/5",  # ⅕
    "\u2156": "2/5",  # ⅖
    "\u2157": "3/5",  # ⅗
    "\u2158": "4/5",  # ⅘
    "\u2159": "1/6",  # ⅙
    "\u215a": "5/6",  # ⅚
    "\u215b": "1/8",  # ⅛
    "\u215c": "3/8",  # ⅜
    "\u215d": "5/8",  # ⅝
    "\u215e": "7/8",  # ⅞
}

# Regex for pricing text: ($0.88), $6.26, $6.26)
_PRICE_RE = re.compile(r"\(\$[\d.]+\)|\$[\d.]+\)?")

# Dual metric/imperial: "1 kg / 2 lb" or "500 g / 1 lb"
_DUAL_UNIT_RE = re.compile(
    r"^([\d.]+)\s*(g|kg|ml|L)\s*/\s*([\d./ ]+)\s*(oz|lb|lbs|cup|cups|tbsp|tsp)\s+(.*)",
    re.IGNORECASE,
)

# Metric units to convert
_METRIC_CONVERSIONS: dict[str, tuple[str, float]] = {
    "g": ("oz", 1 / 28.35),
    "kg": ("lb", 2.205),
    "ml": ("cup", 1 / 237),
    "L": ("cup", 4.227),
}


def _normalize_unicode(text: str) -> str:
    """Replace unicode fraction chars with ASCII equivalents."""
    for char, replacement in _UNICODE_FRACTIONS.items():
        if char in text:
            # Handle combined forms like "1½" → "1 1/2"
            text = re.sub(rf"(\d){re.escape(char)}", rf"\1 {replacement}", text)
            text = text.replace(char, replacement)
    return text


def _to_imperial(qty: float | None, unit: str | None) -> tuple[float | None, str | None]:
    """Convert metric qty/unit to imperial if applicable."""
    if qty is None or unit is None:
        return qty, unit
    if unit in _METRIC_CONVERSIONS:
        imperial_unit, factor = _METRIC_CONVERSIONS[unit]
        return round(qty * factor, 2), imperial_unit
    return qty, unit


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

# Common grocery store brand prefixes to strip
_BRAND_RE = re.compile(
    r"\b(appleton farms|baker'?s corner|chef'?s cupboard|countryside creamery|"
    r"simplynature|stonemill|priano|gold seal|ore[- ]?ida|heinz|bob'?s red mill|"
    r"pace|bertolli|frank'?s|hidden valley|mccormick|old el paso|ro[- ]?tel|"
    r"bush'?s|hunt'?s|del monte|kraft|barilla|season'?s choice|"
    r"cooked perfect|simply nature|mrs\.? dash)\b\s*",
    re.IGNORECASE,
)

# Size words between qty and ingredient name (not units)
_SKIP_WORDS = {"large", "medium", "small", "whole", "extra", "thin", "thick"}

# Descriptors to strip from ingredient names
_DESCRIPTOR_RE = re.compile(
    r"\b("
    r"boneless|skinless|chopped|diced|minced|sliced|shredded|grated|"
    r"melted|softened|crushed|torn|peeled|seeded|trimmed|halved|"
    r"quartered|cubed|julienned|thinly|roughly|finely|coarsely|"
    r"freshly|lightly|well|very|about|approximately|"
    r"cooked|toasted|crumbled|packed|slivered|"
    r"bone-in|skin-on"
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
    """Strip descriptors, parentheticals, and prep instructions from an ingredient name."""
    name = re.sub(r"\([^)]*\)", "", name)
    # Strip unclosed trailing parens: "jalapeño ( into thin rings" → "jalapeño"
    name = re.sub(r"\s*\([^)]*$", "", name)
    # Strip grocery brand prefixes: "Baker's Corner flour" → "flour"
    name = _BRAND_RE.sub("", name)
    # Strip prep instructions after comma BEFORE descriptors (order matters:
    # "spinach, cooked down" → "spinach" not "spinach, down")
    name = re.sub(
        r",\s*(?:cut |into |rinsed|drained|divided|to taste|plus |removed|"
        r"with ribs|with seeds|stemmed|cored|seeded|zested?|juiced|"
        r"undiluted|uncooked|thawed|defrosted|at room temp|see notes|"
        r"fat |and cooked|and |or |green and white|white and green|"
        r"zest and|juice and|juice of|for serving|for garnish|for topping|"
        r"lengthwise|on a |deveined|optional|tightly|cooked|toasted|"
        r"crumbled|packed|beaten|soaked|rough|preferably|seeds ok|"
        # Descriptors that appear between comma and prep instructions:
        r"chopped|diced|minced|sliced|shredded|grated|peeled|"
        r"cubed|julienned|halved|quartered|trimmed|"
        r"finely|roughly|thinly|coarsely|lightly|freshly|"
        r"undrained|pressed|juice |best ).*$",
        "", name, flags=re.IGNORECASE,
    )
    name = _DESCRIPTOR_RE.sub(" ", name)
    name = re.sub(r"\s*,\s*$", "", name)
    name = re.sub(r"^,\s*", "", name)
    # Strip comma followed by weight/count: "zucchini, 1 pound" → "zucchini"
    name = re.sub(r",\s*\d.*$", "", name)
    # Strip "X + Y, for serving" garnish additions
    name = re.sub(r"\s*\+.*$", "", name)
    # Strip trailing lone parens: "tomatoes, )" → "tomatoes,"
    name = re.sub(r"\s*\)\s*$", "", name)
    # Strip leading "of" or "a" from "of cooked bacon", "a jalapeno" etc.
    name = re.sub(r"^(?:of|a)\s+", "", name, flags=re.IGNORECASE)
    # Strip lines that are just topping/optional lists
    lower = name.lower().strip()
    if lower.startswith(("optional:", "toppings:", "toppings!", "other toppings")):
        return ""
    return " ".join(name.split()).strip(" ,;-")


def parse_ingredient_line(line: str) -> tuple[float | None, str | None, str]:
    """Parse a full ingredient line into (qty, unit, name).

    Handles mixed fractions (1 1/2), ranges (1 to 2), unit aliases,
    size words (large, medium), and descriptor stripping.
    """
    text = line.strip()

    # Normalize unicode fractions and strip pricing text
    text = _normalize_unicode(text)
    text = _PRICE_RE.sub("", text).strip()

    # Dual metric/imperial: prefer imperial side
    dual = _DUAL_UNIT_RE.match(text)
    if dual:
        imp_qty_str, imp_unit, rest = dual.group(3), dual.group(4), dual.group(5)
        text = f"{imp_qty_str} {imp_unit} {rest}"

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
            qty, unit = _to_imperial(qty, unit)
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

        qty, unit = _to_imperial(qty, unit)
        return qty, unit, normalize(name) if name else ""

    return None, None, normalize(_clean_name(text))


def _slugify(title: str) -> str:
    """Convert a recipe title to a URL-safe slug ID."""
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return f"url_{slug}"


def _fetch_html(url: str) -> str:
    """Fetch HTML from a URL with anti-bot handling."""
    scraper = cloudscraper.create_scraper()
    resp = scraper.get(url, timeout=15)
    resp.raise_for_status()
    return resp.text


def scrape_recipe(url: str) -> dict[str, Any]:
    """Scrape a recipe URL and return a dict matching insert_recipe_dict() format."""
    html = _fetch_html(url)
    scraper = scrape_html(html, org_url=url)

    title = scraper.title()
    recipe_id = _slugify(title)

    # Parse ingredients into qty/unit/name
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

    # Tags from category
    tags = []
    try:
        cat = scraper.category()
        if cat:
            tags.extend(t.strip().lower() for t in cat.split(",") if t.strip())
    except (AttributeError, NotImplementedError):
        pass

    servings = 4
    try:
        raw_yields = scraper.yields()
        if raw_yields:
            nums = re.findall(r"\d+", raw_yields)
            if nums:
                servings = int(nums[0])
    except (AttributeError, NotImplementedError):
        pass

    image_url = ""
    with contextlib.suppress(AttributeError, NotImplementedError):
        image_url = scraper.image() or ""

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
