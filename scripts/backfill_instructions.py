#!/usr/bin/env python3
"""Scrape source URLs and append instructions to markdown files.

Usage:
    python scripts/backfill_instructions.py
    python scripts/backfill_instructions.py --dry-run
    python scripts/backfill_instructions.py --recipe 50_Taco_Pie
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scraper import scrape_recipe

MEALS_DIR = Path(__file__).parent.parent / "Meals"
URL_FILE = Path(__file__).parent.parent / "data" / "recipe_urls.json"
LOG_FILE = Path(__file__).parent.parent / "data" / "instruction_backfill_log.json"


def load_urls() -> dict[str, str]:
    """Load recipe_id → URL mapping."""
    if not URL_FILE.exists():
        print(f"Error: {URL_FILE} not found")
        sys.exit(1)
    with open(URL_FILE) as f:
        return json.load(f)


def has_instructions(path: Path) -> bool:
    """Check if the markdown already has instructions."""
    text = path.read_text(encoding="utf-8")
    return bool(re.search(r"\*\*Instructions:?\*\*", text))


def append_instructions(path: Path, instructions: str, url: str) -> None:
    """Append instructions to a markdown file."""
    text = path.read_text(encoding="utf-8").rstrip()
    text += f"\n\n**Instructions:**  \n{instructions}\n"
    path.write_text(text, encoding="utf-8")


def backfill_recipe(recipe_id: str, url: str, dry_run: bool = False) -> dict:
    """Scrape instructions from a URL and write to markdown."""
    result = {"recipe_id": recipe_id, "url": url, "status": "ok", "details": ""}

    md_path = MEALS_DIR / f"{recipe_id}.md"
    if not md_path.exists():
        result["status"] = "skipped"
        result["details"] = "Markdown file not found"
        return result

    if has_instructions(md_path):
        result["status"] = "skipped"
        result["details"] = "Already has instructions"
        return result

    try:
        scraped = scrape_recipe(url)
    except Exception as e:
        result["status"] = "scrape_error"
        result["details"] = str(e)
        return result

    instructions = scraped.get("instructions", "").strip()
    if not instructions:
        result["status"] = "no_instructions"
        result["details"] = "Scraper returned empty instructions"
        return result

    result["details"] = f"{len(instructions)} chars"

    if dry_run:
        result["status"] = "dry_run"
        result["instructions_preview"] = instructions[:200]
        return result

    append_instructions(md_path, instructions, url)
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

    total = len(url_map)
    results = []
    ok_count = 0
    skip_count = 0

    print(f"{'[DRY RUN] ' if dry_run else ''}Backfilling instructions for {total} recipes...\n")

    for i, (recipe_id, url) in enumerate(url_map.items(), 1):
        print(f"  [{i}/{total}] {recipe_id}...")
        result = backfill_recipe(recipe_id, url, dry_run=dry_run)
        results.append(result)

        if result["status"] == "ok":
            ok_count += 1
            print(f"    + {result['details']}")
        elif result["status"] == "dry_run":
            ok_count += 1
            print(f"    ~ {result['details']}")
        elif result["status"] == "skipped":
            skip_count += 1
            print(f"    - {result['details']}")
        else:
            print(f"    x {result['status']}: {result['details']}")

        # Rate limit between requests
        if result["status"] not in ("skipped",) and i < total:
            time.sleep(1)

    # Log results
    with open(LOG_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Done!")
    print(f"  Written: {ok_count}")
    print(f"  Skipped: {skip_count}")
    errors = [r for r in results if r["status"] not in ("ok", "dry_run", "skipped")]
    if errors:
        print(f"  Errors: {len(errors)}")
        for e in errors:
            print(f"    - {e['recipe_id']}: {e['details']}")
    print(f"  Log saved to {LOG_FILE}")


if __name__ == "__main__":
    main()
