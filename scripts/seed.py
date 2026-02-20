#!/usr/bin/env python3
"""Fetch recipes from TheMealDB and seed the local database.

Usage:
    python scripts/seed.py              # fetch API → JSON, then load into DB
    python scripts/seed.py --fetch      # only fetch API → seed_data/mealdb_recipes.json
    python scripts/seed.py --load       # only load existing JSON into DB
"""

from __future__ import annotations

import json
import re
import string
import sys
import time
from pathlib import Path

# Add project root to path so 'from src...' imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

from src.database import get_connection, init_db, insert_recipe_dict

SEED_FILE = Path(__file__).parent.parent / "seed_data" / "mealdb_recipes.json"
API_BASE = "https://www.themealdb.com/api/json/v1/1/search.php"

# Map TheMealDB categories to our protein enum values
CATEGORY_TO_PROTEIN: dict[str, str] = {
    "beef": "beef",
    "chicken": "chicken",
    "lamb": "beef",  # closest match
    "pork": "pork",
    "seafood": "fish",
    "goat": "beef",  # closest match
    "vegetarian": "vegetarian",
    "vegan": "vegetarian",
    "pasta": "unknown",
    "starter": "unknown",
    "dessert": "unknown",
    "side": "unknown",
    "breakfast": "eggs",
    "miscellaneous": "unknown",
}

# Regex to parse quantity from measure strings like "2 cups", "100g", "1/2 tsp"
_QTY_RE = re.compile(
    r"""
    ^\s*
    (\d+\s*/\s*\d+    # fraction like 1/2
    |\d+\.?\d*         # decimal like 2 or 2.5
    )
    \s*(.*)$           # rest is unit
    """,
    re.VERBOSE,
)

# Normalize common unit strings
_UNIT_ALIASES: dict[str, str] = {
    "tablespoon": "tbsp",
    "tablespoons": "tbsp",
    "tbsps": "tbsp",
    "tbs": "tbsp",
    "teaspoon": "tsp",
    "teaspoons": "tsp",
    "tsps": "tsp",
    "cup": "cup",
    "cups": "cup",
    "ounce": "oz",
    "ounces": "oz",
    "pound": "lb",
    "pounds": "lb",
    "lbs": "lb",
    "kilogram": "kg",
    "kilograms": "kg",
    "gram": "g",
    "grams": "g",
    "ml": "ml",
    "litre": "L",
    "litres": "L",
    "liter": "L",
    "liters": "L",
    "clove": "clove",
    "cloves": "clove",
    "can": "can",
    "cans": "can",
    "bunch": "bunch",
    "bunches": "bunch",
    "slice": "slice",
    "slices": "slice",
    "piece": "piece",
    "pieces": "piece",
    "sprig": "sprig",
    "sprigs": "sprig",
}


def parse_measure(measure: str) -> tuple[float | None, str | None]:
    """Parse a MealDB measure string into (qty, unit).

    Examples:
        "2 cups"      → (2.0, "cup")
        "100g"        → (100.0, "g")
        "1/2 tsp"     → (0.5, "tsp")
        "pinch"       → (None, None)
        ""            → (None, None)
    """
    text = measure.strip()
    if not text:
        return None, None

    match = _QTY_RE.match(text)
    if not match:
        return None, None

    raw_qty, raw_unit = match.group(1).strip(), match.group(2).strip()

    # Parse quantity (handle fractions)
    if "/" in raw_qty:
        num, denom = raw_qty.split("/")
        qty = float(num.strip()) / float(denom.strip())
    else:
        qty = float(raw_qty)

    # Normalize unit
    unit_lower = raw_unit.lower().rstrip(".")
    unit = _UNIT_ALIASES.get(unit_lower, unit_lower if unit_lower else None)

    return qty, unit


def map_protein(category: str) -> str:
    """Map TheMealDB category to our protein enum value."""
    return CATEGORY_TO_PROTEIN.get(category.lower(), "unknown")


def transform_meal(meal: dict) -> dict:
    """Transform a TheMealDB API meal into our recipe dict format."""
    meal_id = f"mealdb_{meal['idMeal']}"
    category = (meal.get("strCategory") or "").strip()
    area = (meal.get("strArea") or "").strip()

    # Build tags from category + area
    tags = []
    if category:
        tags.append(category.lower())
    if area:
        tags.append(area.lower())
    if meal.get("strTags"):
        for t in meal["strTags"].split(","):
            t = t.strip().lower()
            if t:
                tags.append(t)

    # Parse ingredients
    ingredients = []
    for i in range(1, 21):
        name = (meal.get(f"strIngredient{i}") or "").strip()
        meas = (meal.get(f"strMeasure{i}") or "").strip()
        if not name:
            continue
        qty, unit = parse_measure(meas)
        ingredients.append(
            {
                "raw_text": f"{meas} {name}".strip() if meas else name,
                "normalized_name": name.lower().strip(),
                "is_optional": False,
                "qty": qty,
                "unit": unit,
            }
        )

    return {
        "id": meal_id,
        "title": meal["strMeal"],
        "protein": map_protein(category),
        "prep_notes": "",
        "servings": 4,
        "source_url": meal.get("strSource") or "",
        "source_type": "mealdb",
        "instructions": meal.get("strInstructions") or "",
        "image_url": meal.get("strMealThumb") or "",
        "ingredients": ingredients,
        "tags": list(set(tags)),
    }


def fetch_all_meals() -> list[dict]:
    """Fetch all meals from TheMealDB API (a-z)."""
    all_meals = []
    for letter in string.ascii_lowercase:
        print(f"  Fetching letter '{letter}'...", end=" ", flush=True)
        resp = requests.get(API_BASE, params={"f": letter}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        meals = data.get("meals") or []
        print(f"{len(meals)} recipes")
        all_meals.extend(meals)
        time.sleep(0.5)  # be polite to the free API
    return all_meals


def fetch_and_save() -> list[dict]:
    """Fetch from API, transform, and save to JSON."""
    print("Fetching recipes from TheMealDB API...")
    raw_meals = fetch_all_meals()
    print(f"\nTotal raw meals: {len(raw_meals)}")

    recipes = [transform_meal(m) for m in raw_meals]

    SEED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SEED_FILE, "w") as f:
        json.dump(recipes, f, indent=2)
    print(f"Saved {len(recipes)} recipes to {SEED_FILE}")

    return recipes


def load_into_db(recipes: list[dict] | None = None) -> None:
    """Load recipe dicts into the database."""
    if recipes is None:
        if not SEED_FILE.exists():
            print(f"Error: {SEED_FILE} not found. Run with --fetch first.")
            sys.exit(1)
        with open(SEED_FILE) as f:
            recipes = json.load(f)

    print(f"Loading {len(recipes)} recipes into database...")
    conn = get_connection()
    init_db(conn)

    count = 0
    for recipe in recipes:
        insert_recipe_dict(conn, recipe)
        count += 1

    conn.commit()
    conn.close()
    print(f"Done! {count} MealDB recipes loaded into data/meals.db")


def main() -> None:
    args = sys.argv[1:]

    if "--fetch" in args:
        fetch_and_save()
    elif "--load" in args:
        load_into_db()
    else:
        # Default: fetch + load
        recipes = fetch_and_save()
        load_into_db(recipes)


if __name__ == "__main__":
    main()
