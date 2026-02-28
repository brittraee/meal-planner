"""SQLite database schema and query functions."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from src.models import Recipe

DB_PATH = Path("data/meals.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS recipes (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    prep_notes TEXT,
    source_file TEXT,
    protein TEXT,
    servings INTEGER DEFAULT 4,
    source_url TEXT,
    source_type TEXT DEFAULT 'markdown',
    instructions TEXT,
    image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id TEXT REFERENCES recipes(id),
    raw_text TEXT,
    normalized_name TEXT,
    is_optional INTEGER DEFAULT 0,
    qty REAL,
    unit TEXT
);

CREATE TABLE IF NOT EXISTS recipe_tags (
    recipe_id TEXT REFERENCES recipes(id),
    tag TEXT,
    PRIMARY KEY (recipe_id, tag)
);

CREATE TABLE IF NOT EXISTS meal_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    start_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS planned_meals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER REFERENCES meal_plans(id),
    day_number INTEGER,
    day_label TEXT,
    recipe_id TEXT REFERENCES recipes(id),
    servings INTEGER
);

CREATE TABLE IF NOT EXISTS pantry_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    normalized_name TEXT,
    category TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    servings INTEGER DEFAULT 4,
    meals_per_week INTEGER DEFAULT 5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Get a SQLite connection with row factory enabled."""
    path = db_path or DB_PATH
    if isinstance(path, Path):
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create all tables if they don't exist, then run migrations."""
    conn.executescript(SCHEMA)
    conn.commit()
    _migrate(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns introduced after initial schema (idempotent)."""
    migrations: list[tuple[str, str, str]] = [
        # (table, column, definition)
        ("recipes", "servings", "INTEGER DEFAULT 4"),
        ("recipes", "source_url", "TEXT"),
        ("recipes", "source_type", "TEXT DEFAULT 'markdown'"),
        ("recipes", "instructions", "TEXT"),
        ("recipes", "image_url", "TEXT"),
        ("recipe_ingredients", "qty", "REAL"),
        ("recipe_ingredients", "unit", "TEXT"),
        ("planned_meals", "servings", "INTEGER"),
    ]
    for table, column, definition in migrations:
        existing = {
            row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    conn.commit()


# ---------------------------------------------------------------------------
# Recipe operations
# ---------------------------------------------------------------------------


def insert_recipe(conn: sqlite3.Connection, recipe: Recipe) -> None:
    """Insert a Recipe object into the database.

    Uses INSERT OR REPLACE to support re-importing.  Skips ingredient
    replacement when the recipe already has scraped qty data (prevents
    markdown re-import from wiping backfilled quantities).
    """
    with conn:
        has_qty = conn.execute(
            "SELECT 1 FROM recipe_ingredients WHERE recipe_id = ? AND qty IS NOT NULL LIMIT 1",
            (recipe.filename,),
        ).fetchone()

        conn.execute(
            """INSERT OR REPLACE INTO recipes (id, title, prep_notes, source_file, protein)
               VALUES (?, ?, ?, ?, ?)""",
            (
                recipe.filename,
                recipe.title,
                recipe.prep,
                recipe.filename,
                recipe.protein.value,
            ),
        )

        if not has_qty:
            conn.execute(
                "DELETE FROM recipe_ingredients WHERE recipe_id = ?", (recipe.filename,)
            )
            for ing in recipe.ingredients:
                conn.execute(
                    """INSERT INTO recipe_ingredients
                       (recipe_id, raw_text, normalized_name, is_optional)
                       VALUES (?, ?, ?, ?)""",
                    (recipe.filename, ing.name, ing.normalized, 1 if ing.optional else 0),
                )

        # Tags always refresh (low risk, no qty data)
        conn.execute("DELETE FROM recipe_tags WHERE recipe_id = ?", (recipe.filename,))
        for tag in recipe.tags:
            conn.execute(
                "INSERT OR IGNORE INTO recipe_tags (recipe_id, tag) VALUES (?, ?)",
                (recipe.filename, tag),
            )


def insert_recipe_dict(conn: sqlite3.Connection, data: dict[str, Any]) -> None:
    """Insert a recipe from a dict (for URL import, manual entry, seed data).

    Expected keys: id, title, protein, prep_notes, servings, source_url,
    source_type, instructions, image_url, ingredients (list of dicts with
    raw_text, normalized_name, is_optional, qty, unit), tags (list of str).
    """
    with conn:
        conn.execute(
            """INSERT OR REPLACE INTO recipes
               (id, title, prep_notes, source_file, protein, servings,
                source_url, source_type, instructions, image_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["id"],
                data["title"],
                data.get("prep_notes", ""),
                data.get("source_file", data["id"]),
                data.get("protein", "unknown"),
                data.get("servings", 4),
                data.get("source_url"),
                data.get("source_type", "manual"),
                data.get("instructions"),
                data.get("image_url"),
            ),
        )
        conn.execute("DELETE FROM recipe_ingredients WHERE recipe_id = ?", (data["id"],))
        conn.execute("DELETE FROM recipe_tags WHERE recipe_id = ?", (data["id"],))

        for ing in data.get("ingredients", []):
            conn.execute(
                """INSERT INTO recipe_ingredients
                   (recipe_id, raw_text, normalized_name, is_optional, qty, unit)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    data["id"],
                    ing.get("raw_text", ing.get("name", "")),
                    ing.get("normalized_name", ing.get("name", "").lower().strip()),
                    1 if ing.get("is_optional") else 0,
                    ing.get("qty"),
                    ing.get("unit"),
                ),
            )

        for tag in data.get("tags", []):
            conn.execute(
                "INSERT OR IGNORE INTO recipe_tags (recipe_id, tag) VALUES (?, ?)",
                (data["id"], tag),
            )


def get_all_recipes(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Get all recipes ordered by title."""
    rows = conn.execute(
        "SELECT id, title, protein, prep_notes, source_file FROM recipes ORDER BY title"
    ).fetchall()
    return [dict(row) for row in rows]


def get_unique_tags(conn: sqlite3.Connection) -> list[str]:
    """Get all unique tags sorted alphabetically."""
    rows = conn.execute("SELECT DISTINCT tag FROM recipe_tags ORDER BY tag").fetchall()
    return [row["tag"] for row in rows]


def get_unique_proteins(conn: sqlite3.Connection) -> list[str]:
    """Get all unique protein values (excluding 'unknown')."""
    rows = conn.execute(
        "SELECT DISTINCT protein FROM recipes WHERE protein != 'unknown' ORDER BY protein"
    ).fetchall()
    return [row["protein"] for row in rows]


def search_recipes(
    conn: sqlite3.Connection,
    query: str | None = None,
    tags: list[str] | None = None,
    protein: str | None = None,
    max_time: int | None = None,
    ingredients: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Search recipes with optional filters.
    """
    # Subquery to collect tags per recipe (GROUP_CONCAT)
    sql = """
        SELECT r.id, r.title, r.protein, r.prep_notes, r.source_file,
               r.source_type,
               (SELECT GROUP_CONCAT(rt2.tag, ',')
                FROM recipe_tags rt2 WHERE rt2.recipe_id = r.id) AS tags_csv
        FROM recipes r
        LEFT JOIN recipe_tags rt ON r.id = rt.recipe_id
        LEFT JOIN recipe_ingredients ri ON r.id = ri.recipe_id
        WHERE 1=1
    """
    params: list[Any] = []

    if tags:
        placeholders = ", ".join("?" for _ in tags)
        sql += f" AND rt.tag IN ({placeholders})"
        params.extend(tags)

    if protein:
        sql += " AND r.protein = ?"
        params.append(protein)

    if query:
        sql += " AND (r.title LIKE ? OR ri.normalized_name LIKE ?)"
        params.extend([f"%{query}%", f"%{query}%"])

    if max_time is not None:
        # Match recipes that have a time tag <= max_time (e.g. "30min")
        time_tags = [f"{m}min" for m in range(1, max_time + 1)]
        placeholders = ", ".join("?" for _ in time_tags)
        sql += f"""
            AND r.id IN (
                SELECT rt3.recipe_id FROM recipe_tags rt3
                WHERE rt3.tag IN ({placeholders})
            )
        """
        params.extend(time_tags)

    if ingredients:
        # Match recipes by protein column OR ingredient name (LIKE for partial)
        protein_ph = ", ".join("?" for _ in ingredients)
        like_clauses = " OR ".join("ri2.normalized_name LIKE ?" for _ in ingredients)
        sql += f"""
            AND (
                r.protein IN ({protein_ph})
                OR r.id IN (
                    SELECT ri2.recipe_id FROM recipe_ingredients ri2
                    WHERE {like_clauses}
                )
            )
        """
        params.extend(ingredients)
        params.extend(f"%{ing}%" for ing in ingredients)

    sql += " GROUP BY r.id ORDER BY r.title"

    rows = conn.execute(sql, params).fetchall()
    results = []
    for row in rows:
        d = dict(row)
        d["tags"] = d["tags_csv"].split(",") if d.get("tags_csv") else []
        del d["tags_csv"]
        results.append(d)
    return results


def get_recipe_details(conn: sqlite3.Connection, recipe_id: str) -> dict[str, Any] | None:
    """Get a single recipe with its ingredients and tags."""
    row = conn.execute(
        """SELECT id, title, protein, prep_notes, source_file, servings,
                  source_type, instructions, image_url
           FROM recipes WHERE id = ?""",
        (recipe_id,),
    ).fetchone()
    if not row:
        return None

    result = dict(row)

    ingredients = conn.execute(
        """SELECT raw_text, normalized_name, is_optional, qty, unit
           FROM recipe_ingredients WHERE recipe_id = ? ORDER BY id""",
        (recipe_id,),
    ).fetchall()
    result["ingredients"] = [dict(i) for i in ingredients]

    tags = conn.execute(
        "SELECT tag FROM recipe_tags WHERE recipe_id = ? ORDER BY tag",
        (recipe_id,),
    ).fetchall()
    result["tags"] = [t["tag"] for t in tags]

    return result


# ---------------------------------------------------------------------------
# Meal plan operations
# ---------------------------------------------------------------------------


def create_meal_plan(
    conn: sqlite3.Connection,
    name: str,
    start_date: str,
    meals: list[tuple[int, str, str]] | list[tuple[int, str, str, int]],
) -> int:
    """Create a meal plan with planned meals.

    Args:
        meals: List of (day_number, day_label, recipe_id) or
               (day_number, day_label, recipe_id, servings) tuples.

    Returns:
        The new plan's ID.
    """
    cursor = conn.execute(
        "INSERT INTO meal_plans (name, start_date) VALUES (?, ?)",
        (name, start_date),
    )
    plan_id = cursor.lastrowid

    for meal in meals:
        day_number, day_label, recipe_id = meal[0], meal[1], meal[2]
        servings = meal[3] if len(meal) > 3 else None
        conn.execute(
            """INSERT INTO planned_meals (plan_id, day_number, day_label, recipe_id, servings)
               VALUES (?, ?, ?, ?, ?)""",
            (plan_id, day_number, day_label, recipe_id, servings),
        )

    conn.commit()
    return plan_id


def get_meal_plans(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Get all meal plans with meal count, most recent first."""
    rows = conn.execute(
        """SELECT mp.id, mp.name, mp.start_date, mp.created_at,
                  COUNT(pm.id) as meal_count
           FROM meal_plans mp
           LEFT JOIN planned_meals pm ON mp.id = pm.plan_id
           GROUP BY mp.id
           ORDER BY mp.created_at DESC"""
    ).fetchall()
    return [dict(row) for row in rows]


def get_planned_meals(conn: sqlite3.Connection, plan_id: int) -> list[dict[str, Any]]:
    """Get all meals in a plan with recipe details."""
    rows = conn.execute(
        """SELECT pm.day_number, pm.day_label, pm.recipe_id,
                  r.title, r.protein, r.prep_notes,
                  COALESCE(pm.servings, r.servings) as servings
           FROM planned_meals pm
           JOIN recipes r ON pm.recipe_id = r.id
           WHERE pm.plan_id = ?
           ORDER BY pm.day_number""",
        (plan_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def delete_meal_plan(conn: sqlite3.Connection, plan_id: int) -> None:
    """Delete a meal plan and its planned meals."""
    conn.execute("DELETE FROM planned_meals WHERE plan_id = ?", (plan_id,))
    conn.execute("DELETE FROM meal_plans WHERE id = ?", (plan_id,))
    conn.commit()


# ---------------------------------------------------------------------------
# Pantry operations
# ---------------------------------------------------------------------------


def add_pantry_item(
    conn: sqlite3.Connection,
    name: str,
    normalized_name: str,
    category: str = "staples",
) -> int:
    """Add an item to the pantry. Returns the new item's ID."""
    cursor = conn.execute(
        "INSERT INTO pantry_items (name, normalized_name, category) VALUES (?, ?, ?)",
        (name, normalized_name, category),
    )
    conn.commit()
    return cursor.lastrowid


def get_pantry_items(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Get all pantry items ordered by category then name."""
    rows = conn.execute(
        "SELECT id, name, normalized_name, category FROM pantry_items ORDER BY category, name"
    ).fetchall()
    return [dict(row) for row in rows]


def delete_pantry_item(conn: sqlite3.Connection, item_id: int) -> None:
    """Delete a pantry item by ID."""
    conn.execute("DELETE FROM pantry_items WHERE id = ?", (item_id,))
    conn.commit()


def clear_pantry(conn: sqlite3.Connection) -> None:
    """Remove all pantry items."""
    conn.execute("DELETE FROM pantry_items")
    conn.commit()


# ---------------------------------------------------------------------------
# Shopping list query
# ---------------------------------------------------------------------------


def get_shopping_list(conn: sqlite3.Connection, plan_id: int) -> list[dict[str, Any]]:
    """Get consolidated shopping list for a meal plan.

    Returns per-ingredient rows with qty/unit scaled by servings overrides.
    Each row: normalized_name, needed_for, display_name, in_pantry, qty, unit.
    """
    rows = conn.execute(
        """SELECT ri.normalized_name,
                  r.title as recipe_title,
                  ri.raw_text as display_name,
                  ri.qty,
                  ri.unit,
                  r.servings as recipe_servings,
                  pm.servings as plan_servings,
                  EXISTS(
                      SELECT 1 FROM pantry_items pi
                      WHERE pi.normalized_name = ri.normalized_name
                  ) as in_pantry
           FROM planned_meals pm
           JOIN recipe_ingredients ri ON pm.recipe_id = ri.recipe_id
           JOIN recipes r ON pm.recipe_id = r.id
           WHERE pm.plan_id = ? AND ri.is_optional = 0
           ORDER BY ri.normalized_name""",
        (plan_id,),
    ).fetchall()

    # Aggregate: group by normalized_name, scale quantities, merge recipe titles
    groups: dict[str, dict[str, Any]] = {}
    for row in rows:
        row = dict(row)
        name = row["normalized_name"]

        # Scale quantity by servings ratio if both are available
        qty = row["qty"]
        if qty and row["plan_servings"] and row["recipe_servings"]:
            qty = qty * row["plan_servings"] / row["recipe_servings"]

        # Group by name+unit so mismatched units stay as separate lines
        unit = row["unit"]
        key = (name, unit)

        if key not in groups:
            groups[key] = {
                "normalized_name": name,
                "display_name": row["display_name"],
                "needed_for": row["recipe_title"],
                "in_pantry": row["in_pantry"],
                "qty": qty,
                "unit": unit,
                "_recipes": {row["recipe_title"]},
            }
        else:
            entry = groups[key]
            entry["_recipes"].add(row["recipe_title"])
            entry["needed_for"] = ", ".join(sorted(entry["_recipes"]))
            if qty and entry["qty"]:
                entry["qty"] += qty
            elif qty and not entry["qty"]:
                entry["qty"] = qty

    result = []
    for entry in groups.values():
        entry.pop("_recipes", None)
        result.append(entry)

    result.sort(key=lambda x: (x["in_pantry"], x["normalized_name"]))
    return result


# ---------------------------------------------------------------------------
# Analytics queries
# ---------------------------------------------------------------------------


def get_recipe_count_by_protein(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Count recipes by protein type."""
    rows = conn.execute(
        """SELECT protein, COUNT(*) as count
           FROM recipes
           GROUP BY protein
           ORDER BY count DESC"""
    ).fetchall()
    return [dict(row) for row in rows]


def get_recipe_history(conn: sqlite3.Connection, recipe_id: str) -> list[dict[str, Any]]:
    """Get the meal plan history for a specific recipe."""
    rows = conn.execute(
        """SELECT mp.name as plan_name, mp.start_date, pm.day_label
           FROM planned_meals pm
           JOIN meal_plans mp ON pm.plan_id = mp.id
           WHERE pm.recipe_id = ?
           ORDER BY mp.start_date DESC""",
        (recipe_id,),
    ).fetchall()
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# User settings (onboarding)
# ---------------------------------------------------------------------------


def has_completed_onboarding(conn: sqlite3.Connection) -> bool:
    """Check if the user has completed the onboarding flow."""
    row = conn.execute("SELECT 1 FROM user_settings WHERE id = 1").fetchone()
    return row is not None


def get_user_settings(conn: sqlite3.Connection) -> dict[str, Any] | None:
    """Get user settings, or None if onboarding hasn't been completed."""
    row = conn.execute("SELECT * FROM user_settings WHERE id = 1").fetchone()
    return dict(row) if row else None


def delete_recipe(conn: sqlite3.Connection, recipe_id: str) -> None:
    """Delete a recipe and its ingredients/tags."""
    conn.execute("DELETE FROM recipe_ingredients WHERE recipe_id = ?", (recipe_id,))
    conn.execute("DELETE FROM recipe_tags WHERE recipe_id = ?", (recipe_id,))
    conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    conn.commit()


def clear_user_data(conn: sqlite3.Connection) -> None:
    """Clear user data (settings, pantry, plans). Keeps recipe library."""
    conn.execute("DELETE FROM planned_meals")
    conn.execute("DELETE FROM meal_plans")
    conn.execute("DELETE FROM pantry_items")
    conn.execute("DELETE FROM user_settings")
    conn.commit()


def save_user_settings(
    conn: sqlite3.Connection,
    servings: int,
    meals_per_week: int,
) -> None:
    """Save or update user settings (single-row table)."""
    conn.execute(
        """INSERT OR REPLACE INTO user_settings (id, servings, meals_per_week)
           VALUES (1, ?, ?)""",
        (servings, meals_per_week),
    )
    conn.commit()
