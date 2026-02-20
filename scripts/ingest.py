#!/usr/bin/env python3
"""Ingest recipe Markdown files into the SQLite database.

Usage:
    python scripts/ingest.py
    python scripts/ingest.py --meals-dir /path/to/Meals
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path so 'from src...' imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_connection, init_db, insert_recipe
from src.recipe_parser import parse_recipes

MEALS_DIR = Path(__file__).parent.parent / "Meals"


def main(meals_dir: Path | None = None) -> None:
    """Parse all recipe cards and populate the database."""
    directory = meals_dir or MEALS_DIR

    if not directory.exists():
        print(f"Error: Meals directory not found at {directory}")
        sys.exit(1)

    print(f"Parsing recipes from {directory}...")
    recipes = parse_recipes(directory)
    print(f"Found {len(recipes)} recipes")

    conn = get_connection()
    init_db(conn)

    for recipe in recipes:
        insert_recipe(conn, recipe)
        print(f"  + {recipe.title} ({recipe.protein.value})")

    conn.commit()
    conn.close()

    print(f"\nDone! {len(recipes)} recipes imported to data/meals.db")


if __name__ == "__main__":
    # Support optional --meals-dir argument
    if len(sys.argv) > 2 and sys.argv[1] == "--meals-dir":
        main(Path(sys.argv[2]))
    else:
        main()
