#!/usr/bin/env python3
"""Backfill ingredient quantities by scraping real recipe URLs.

Reads recipe_urls.json, scrapes each URL, and updates the database with
real ingredient quantities. Preserves existing recipe metadata (title,
protein, tags) — only replaces ingredient rows.

Usage:
    python scripts/backfill_quantities.py
    python scripts/backfill_quantities.py --dry-run
    python scripts/backfill_quantities.py --recipe 252_Classic_Cheeseburgers
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_connection, init_db
from src.scraper import scrape_recipe

URL_FILE = Path(__file__).parent.parent / "data" / "recipe_urls.json"
LOG_FILE = Path(__file__).parent.parent / "data" / "backfill_log.json"


def load_urls() -> dict[str, str]:
    """Load recipe_id → URL mapping."""
    if not URL_FILE.exists():
        print(f"Error: {URL_FILE} not found")
        sys.exit(1)
    with open(URL_FILE) as f:
        return json.load(f)


def backfill_recipe(conn, recipe_id: str, url: str, dry_run: bool = False) -> dict:
    """Scrape a URL and update ingredient quantities for a recipe.

    Returns a result dict with status and details.
    """
    result = {"recipe_id": recipe_id, "url": url, "status": "ok", "details": ""}

    # Skip if recipe doesn't exist in DB (orphaned URL entry)
    exists = conn.execute(
        "SELECT 1 FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()
    if not exists:
        result["status"] = "skipped"
        result["details"] = "Recipe not in database"
        return result

    try:
        scraped = scrape_recipe(url)
    except Exception as e:
        result["status"] = "scrape_error"
        result["details"] = str(e)
        return result

    if not scraped["ingredients"]:
        result["status"] = "no_ingredients"
        result["details"] = "Scraper returned 0 ingredients"
        return result

    # Count how many have qty
    with_qty = sum(1 for i in scraped["ingredients"] if i["qty"] is not None)
    total = len(scraped["ingredients"])
    result["details"] = f"{with_qty}/{total} ingredients have quantities"

    if dry_run:
        result["status"] = "dry_run"
        result["ingredients"] = [
            {
                "name": i["normalized_name"],
                "qty": i["qty"],
                "unit": i["unit"],
                "raw": i["raw_text"],
            }
            for i in scraped["ingredients"]
        ]
        return result

    # Replace ingredient rows with scraped data (preserves recipe metadata)
    conn.execute("DELETE FROM recipe_ingredients WHERE recipe_id = ?", (recipe_id,))
    for ing in scraped["ingredients"]:
        conn.execute(
            """INSERT INTO recipe_ingredients
               (recipe_id, raw_text, normalized_name, is_optional, qty, unit)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                recipe_id,
                ing["raw_text"],
                ing["normalized_name"],
                1 if ing.get("is_optional") else 0,
                ing.get("qty"),
                ing.get("unit"),
            ),
        )

    # Update servings and source_url on the recipe
    conn.execute(
        "UPDATE recipes SET servings = ?, source_url = ? WHERE id = ?",
        (scraped.get("servings", 4), url, recipe_id),
    )
    conn.commit()

    return result


def main():
    dry_run = "--dry-run" in sys.argv
    single_recipe = None
    for i, arg in enumerate(sys.argv):
        if arg == "--recipe" and i + 1 < len(sys.argv):
            single_recipe = sys.argv[i + 1]

    url_map = load_urls()
    if single_recipe:
        if single_recipe not in url_map:
            print(f"Recipe '{single_recipe}' not found in {URL_FILE}")
            sys.exit(1)
        url_map = {single_recipe: url_map[single_recipe]}

    conn = get_connection()
    init_db(conn)

    total = len(url_map)
    results = []
    ok_count = 0

    print(f"{'[DRY RUN] ' if dry_run else ''}Backfilling {total} recipes...\n")

    for i, (recipe_id, url) in enumerate(url_map.items(), 1):
        print(f"  [{i}/{total}] {recipe_id}...")
        result = backfill_recipe(conn, recipe_id, url, dry_run=dry_run)
        results.append(result)

        if result["status"] == "ok":
            ok_count += 1
            print(f"    ✓ {result['details']}")
        elif result["status"] == "dry_run":
            print(f"    ~ {result['details']}")
        elif result["status"] == "skipped":
            print(f"    ⊘ {result['details']}")
        else:
            print(f"    ✗ {result['status']}: {result['details']}")

        # Rate limit: 1 second between requests
        if i < total:
            time.sleep(1)

    conn.close()

    # Save log
    with open(LOG_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Done!")
    print(f"  Success: {ok_count}/{total}")
    errors = [r for r in results if r["status"] not in ("ok", "dry_run")]
    if errors:
        print(f"  Errors: {len(errors)}")
        for e in errors:
            print(f"    - {e['recipe_id']}: {e['details']}")
    print(f"  Log saved to {LOG_FILE}")


if __name__ == "__main__":
    main()
