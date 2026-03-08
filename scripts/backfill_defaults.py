#!/usr/bin/env python3
"""Backfill NULL ingredient quantities with smart defaults.

Applies per-serving defaults from QUANTITY_DEFAULTS to existing rows that
have no qty data (qty IS NULL and qty_source is not scraped/manual).

Usage:
    python scripts/backfill_defaults.py --dry-run
    python scripts/backfill_defaults.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_connection, init_db
from src.ingredients import get_default_qty, normalize

LOG_FILE = Path(__file__).parent.parent / "data" / "backfill_defaults_log.json"


def main():
    dry_run = "--dry-run" in sys.argv

    conn = get_connection()
    init_db(conn)

    # Find all ingredient rows with no qty and no higher-priority source
    rows = conn.execute(
        """SELECT ri.id, ri.recipe_id, ri.normalized_name, r.servings
           FROM recipe_ingredients ri
           JOIN recipes r ON ri.recipe_id = r.id
           WHERE ri.qty IS NULL
             AND (ri.qty_source IS NULL OR ri.qty_source = '')"""
    ).fetchall()

    total = len(rows)
    updated = 0
    skipped = 0
    results = []

    print(f"{'[DRY RUN] ' if dry_run else ''}Found {total} rows with NULL qty\n")

    for row in rows:
        row = dict(row)
        name = row["normalized_name"]
        # Re-normalize through aliases (DB may store pre-alias names)
        canonical = normalize(name)
        base_servings = row["servings"] or 4
        dq, du = get_default_qty(canonical)

        entry = {
            "id": row["id"],
            "recipe_id": row["recipe_id"],
            "normalized_name": name,
        }

        if dq is None:
            entry["status"] = "no_default"
            skipped += 1
        else:
            qty = dq * base_servings
            entry["status"] = "dry_run" if dry_run else "updated"
            entry["qty"] = qty
            entry["unit"] = du

            if not dry_run:
                conn.execute(
                    "UPDATE recipe_ingredients SET qty = ?, unit = ?, qty_source = 'default' WHERE id = ?",
                    (qty, du, row["id"]),
                )
                updated += 1
            else:
                updated += 1

        results.append(entry)

    if not dry_run:
        conn.commit()

    conn.close()

    with open(LOG_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"{'[DRY RUN] ' if dry_run else ''}Done!")
    print(f"  Updated: {updated}/{total}")
    print(f"  No default found: {skipped}")
    print(f"  Log saved to {LOG_FILE}")


if __name__ == "__main__":
    main()
