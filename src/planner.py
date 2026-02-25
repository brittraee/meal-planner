"""Meal plan generation using Pandas DataFrames."""

from __future__ import annotations

import random
import sqlite3

import pandas as pd

DAY_LABELS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def generate_plan(
    conn: sqlite3.Connection,
    days: int = 5,
    excluded_ingredients: list[str] | None = None,
    included_ingredients: list[str] | None = None,
    require_included: bool = False,
    diet: str = "omnivore",
    seed: int | None = None,
    start_day: str = "Monday",
    pinned_any: list[str] | None = None,
    pinned_fixed: list[tuple[int, str]] | None = None,
    priority_tags: list[str] | None = None,
) -> pd.DataFrame:
    """Generate a meal plan using Pandas DataFrame operations.

    Returns a DataFrame with columns:
        day, day_label, recipe_id, title, protein, prep_notes, servings,
        score, pantry_matches, tag_bonuses
    """
    if seed is None:
        seed = random.randint(0, 2**31 - 1)

    pinned_any = pinned_any or []
    pinned_fixed = pinned_fixed or []
    all_pinned_ids = set(pinned_any) | {rid for _, rid in pinned_fixed}

    # --- Load data from SQLite into DataFrames ---
    recipes_df = pd.read_sql(
        "SELECT id, title, protein, prep_notes, servings FROM recipes", conn
    )
    tags_df = pd.read_sql("SELECT recipe_id, tag FROM recipe_tags", conn)
    ingredients_df = pd.read_sql(
        "SELECT recipe_id, normalized_name FROM recipe_ingredients WHERE is_optional = 0",
        conn,
    )

    if recipes_df.empty:
        raise ValueError("No recipes in database. Run: python scripts/ingest.py")

    # Load pantry items for scoring
    pantry_rows = conn.execute(
        "SELECT normalized_name, name FROM pantry_items"
    ).fetchall()
    pantry_set = {r["normalized_name"] for r in pantry_rows}
    pantry_display = {r["normalized_name"]: r["name"] for r in pantry_rows}

    # Per-recipe ingredient lookup
    recipe_ing_map = (
        ingredients_df.groupby("recipe_id")["normalized_name"]
        .apply(set)
        .to_dict()
    )

    # Separate pinned recipes before filtering (pinned skip filters)
    pinned_df = recipes_df[recipes_df["id"].isin(all_pinned_ids)].copy()
    pool_df = recipes_df[~recipes_df["id"].isin(all_pinned_ids)].copy()

    # --- Filtering (only on the non-pinned pool) ---

    if diet == "vegetarian":
        pool_df = pool_df.query("protein in ['vegetarian', 'eggs', 'unknown']")
    elif diet == "pescatarian":
        meat_proteins = ["chicken", "beef", "pork"]
        pool_df = pool_df[~pool_df["protein"].isin(meat_proteins)]

    if excluded_ingredients:
        excluded_set = {ing.lower() for ing in excluded_ingredients}
        bad_ids = ingredients_df[ingredients_df["normalized_name"].isin(excluded_set)][
            "recipe_id"
        ].unique()
        pool_df = pool_df[~pool_df["id"].isin(bad_ids)]

    if included_ingredients and require_included:
        included_set = {ing.lower() for ing in included_ingredients}
        good_ids = ingredients_df[ingredients_df["normalized_name"].isin(included_set)][
            "recipe_id"
        ].unique()
        pool_df = pool_df[pool_df["id"].isin(good_ids)]

    # Check if we have enough recipes (pool + pinned) to fill the plan
    total_available = len(pool_df) + len(all_pinned_ids)
    if total_available == 0:
        raise ValueError("No recipes match the given constraints")

    # --- Scoring with evidence tracking ---

    pool_df = pool_df.assign(score=0)
    evidence: dict[str, dict] = {}
    for rid in pool_df["id"]:
        evidence[rid] = {"pantry_matches": [], "tag_bonuses": []}

    # Pantry match bonus (+3)
    if pantry_set:
        pantry_boosted = []
        for rid in pool_df["id"]:
            matches = recipe_ing_map.get(rid, set()) & pantry_set
            if matches:
                evidence[rid]["pantry_matches"] = sorted(
                    pantry_display.get(m, m) for m in matches
                )
                pantry_boosted.append(rid)
        pool_df.loc[pool_df["id"].isin(pantry_boosted), "score"] += 3

    # Included ingredient bonus (+3)
    if included_ingredients and not require_included:
        included_set = {ing.lower() for ing in included_ingredients}
        boosted_ids = ingredients_df[ingredients_df["normalized_name"].isin(included_set)][
            "recipe_id"
        ].unique()
        pool_df.loc[pool_df["id"].isin(boosted_ids), "score"] += 3

    # Quick/easy tag bonus (+1)
    quick_tags = {"quick", "quickmeal", "easy", "fastdinner", "lowspoon"}
    quick_ids = tags_df[tags_df["tag"].isin(quick_tags)]["recipe_id"].unique()
    pool_df.loc[pool_df["id"].isin(quick_ids), "score"] += 1
    for rid in quick_ids:
        if rid in evidence:
            evidence[rid]["tag_bonuses"].append("quick/easy")

    # Kid-friendly bonus (+1)
    kid_tags = {"kidfriendly", "familyfriendly"}
    kid_ids = tags_df[tags_df["tag"].isin(kid_tags)]["recipe_id"].unique()
    pool_df.loc[pool_df["id"].isin(kid_ids), "score"] += 1
    for rid in kid_ids:
        if rid in evidence:
            evidence[rid]["tag_bonuses"].append("kid-friendly")

    # Priority tag bonus (+2)
    if priority_tags:
        priority_set = {t.lower() for t in priority_tags}
        priority_ids = tags_df[tags_df["tag"].isin(priority_set)]["recipe_id"].unique()
        pool_df.loc[pool_df["id"].isin(priority_ids), "score"] += 2
        for rid in priority_ids:
            if rid in evidence:
                matching = tags_df[
                    (tags_df["recipe_id"] == rid) & (tags_df["tag"].isin(priority_set))
                ]["tag"].tolist()
                evidence[rid]["tag_bonuses"].extend(matching)

    # Serialize evidence into pool_df columns
    pool_df["pantry_matches"] = pool_df["id"].map(
        lambda rid: ", ".join(evidence.get(rid, {}).get("pantry_matches", []))
    )
    pool_df["tag_bonuses"] = pool_df["id"].map(
        lambda rid: ", ".join(evidence.get(rid, {}).get("tag_bonuses", []))
    )

    # --- Tag count as tiebreaker ---

    tag_counts = tags_df.groupby("recipe_id").size().reset_index(name="tag_count")
    pool_df = pool_df.merge(tag_counts, left_on="id", right_on="recipe_id", how="left")
    pool_df["tag_count"] = pool_df["tag_count"].fillna(0).astype(int)
    pool_df = pool_df.drop(columns=["recipe_id"], errors="ignore")

    # Weighted shuffle
    if not pool_df.empty:
        weights = pool_df["score"] + 1
        pool_df = pool_df.sample(
            frac=1, random_state=seed, weights=weights
        ).reset_index(drop=True)

    # --- Place pinned recipes, then fill remaining slots ---

    start_idx = DAY_LABELS.index(start_day) if start_day in DAY_LABELS else 0

    # Helper: compute pantry matches for pinned recipes (they skip scoring)
    def _pinned_pantry(recipe_id: str) -> str:
        matches = recipe_ing_map.get(recipe_id, set()) & pantry_set
        if matches:
            return ", ".join(sorted(pantry_display.get(m, m) for m in matches))
        return ""

    # Initialize result slots (None = unfilled)
    slots: list[dict | None] = [None] * days
    used_ids: set[str] = set()

    # Place fixed-day pins
    for day_idx, recipe_id in pinned_fixed:
        if day_idx < days:
            row = pinned_df[pinned_df["id"] == recipe_id]
            if not row.empty:
                r = row.iloc[0]
                slots[day_idx] = {
                    "id": r["id"],
                    "title": r["title"],
                    "protein": r["protein"],
                    "prep_notes": r["prep_notes"],
                    "servings": r.get("servings", 4) or 4,
                    "score": 0,
                    "pantry_matches": _pinned_pantry(recipe_id),
                    "tag_bonuses": "pinned",
                }
                used_ids.add(recipe_id)

    # Place "any day" pins in open slots (respecting variety where possible)
    for recipe_id in pinned_any:
        if recipe_id in used_ids:
            continue
        row = pinned_df[pinned_df["id"] == recipe_id]
        if row.empty:
            continue
        r = row.iloc[0]
        recipe_dict = {
            "id": r["id"],
            "title": r["title"],
            "protein": r["protein"],
            "prep_notes": r["prep_notes"],
            "servings": r.get("servings", 4) or 4,
            "score": 0,
            "pantry_matches": _pinned_pantry(recipe_id),
            "tag_bonuses": "pinned",
        }
        # Find best open slot (prefer one where neighbors have different protein)
        best_slot = None
        for i in range(days):
            if slots[i] is not None:
                continue
            prev_protein = slots[i - 1]["protein"] if i > 0 and slots[i - 1] else None
            next_protein = slots[i + 1]["protein"] if i < days - 1 and slots[i + 1] else None
            if r["protein"] != prev_protein and r["protein"] != next_protein:
                best_slot = i
                break
            if best_slot is None:
                best_slot = i  # fallback: first open slot
        if best_slot is not None:
            slots[best_slot] = recipe_dict
            used_ids.add(recipe_id)

    # Fill remaining open slots from the scored pool
    if not pool_df.empty:
        remaining_pool = pool_df[~pool_df["id"].isin(used_ids)]
        pool_rows = _select_with_variety_for_slots(remaining_pool, slots)
        pool_iter = iter(pool_rows)
        for i in range(days):
            if slots[i] is None:
                try:
                    slots[i] = next(pool_iter)
                except StopIteration:
                    break

    # Build result DataFrame
    result = pd.DataFrame(
        [
            {
                "day": i + 1,
                "day_label": DAY_LABELS[(start_idx + i) % 7],
                "recipe_id": slot["id"],
                "title": slot["title"],
                "protein": slot["protein"],
                "prep_notes": slot["prep_notes"],
                "servings": slot.get("servings", 4) or 4,
                "score": slot.get("score", 0),
                "pantry_matches": slot.get("pantry_matches", ""),
                "tag_bonuses": slot.get("tag_bonuses", ""),
            }
            for i, slot in enumerate(slots)
            if slot is not None
        ]
    )

    return result


def _select_with_variety_for_slots(
    df: pd.DataFrame, slots: list[dict | None]
) -> list[dict]:
    """Select recipes to fill None slots, respecting variety with pre-filled neighbors."""
    needed = sum(1 for s in slots if s is None)
    if needed == 0:
        return []

    selected: list[dict] = []
    used_indices: set[int] = set()

    for i, slot in enumerate(slots):
        if slot is not None:
            continue
        # Determine neighboring proteins (from filled slots or already-selected fills)
        prev_protein = None
        if i > 0:
            prev_protein = slots[i - 1]["protein"] if slots[i - 1] else None
        next_protein = None
        if i < len(slots) - 1:
            next_protein = slots[i + 1]["protein"] if slots[i + 1] else None

        picked = _pick_next_avoiding(df, used_indices, prev_protein, next_protein)
        if picked is None:
            picked = _pick_next_avoiding(df, used_indices, None, None)
        if picked is None:
            used_indices.clear()
            picked = _pick_next_avoiding(df, used_indices, None, None)
        if picked is None:
            break

        idx, row = picked
        selected.append(row)
        used_indices.add(idx)
        # Update slot so next iteration can see this as a neighbor
        slots[i] = row

    return selected


def _pick_next_avoiding(
    df: pd.DataFrame,
    used_indices: set[int],
    prev_protein: str | None,
    next_protein: str | None,
) -> tuple[int, dict] | None:
    """Pick next recipe avoiding specified neighbor proteins."""
    for idx in df.index:
        if idx in used_indices:
            continue
        row = df.loc[idx]
        protein = row["protein"]
        if protein != "unknown":
            if prev_protein and protein == prev_protein:
                continue
            if next_protein and protein == next_protein:
                continue
        return idx, row.to_dict()

    # Fallback: ignore constraints
    for idx in df.index:
        if idx in used_indices:
            continue
        return idx, df.loc[idx].to_dict()

    return None


def pick_replacement(
    conn: sqlite3.Connection,
    plan_df: pd.DataFrame,
    day_index: int,
) -> dict:
    """Pick a single replacement recipe for one day in an existing plan.

    Avoids recipes already in the plan and tries to pick a different protein
    than the neighboring days.
    """
    used_ids = set(plan_df["recipe_id"].tolist())
    recipes_df = pd.read_sql(
        "SELECT id, title, protein, prep_notes, servings FROM recipes", conn
    )
    ingredients_df = pd.read_sql(
        "SELECT recipe_id, normalized_name FROM recipe_ingredients WHERE is_optional = 0",
        conn,
    )
    pantry_rows = conn.execute(
        "SELECT normalized_name, name FROM pantry_items"
    ).fetchall()
    pantry_set = {r["normalized_name"] for r in pantry_rows}
    pantry_display = {r["normalized_name"]: r["name"] for r in pantry_rows}

    # Exclude recipes already in the plan
    candidates = recipes_df[~recipes_df["id"].isin(used_ids)]
    if candidates.empty:
        candidates = recipes_df  # fallback: allow repeats

    # Determine neighbor proteins to avoid
    avoid_proteins = set()
    if day_index > 0:
        avoid_proteins.add(plan_df.iloc[day_index - 1]["protein"])
    if day_index < len(plan_df) - 1:
        avoid_proteins.add(plan_df.iloc[day_index + 1]["protein"])

    # Prefer candidates with different protein than neighbors
    preferred = candidates[~candidates["protein"].isin(avoid_proteins)]
    pool = preferred if not preferred.empty else candidates

    pick = pool.sample(1).iloc[0]

    # Compute pantry matches for the replacement
    recipe_ings = set(
        ingredients_df[ingredients_df["recipe_id"] == pick["id"]]["normalized_name"]
    )
    matches = recipe_ings & pantry_set
    pantry_str = ", ".join(sorted(pantry_display.get(m, m) for m in matches))

    return {
        "recipe_id": pick["id"],
        "title": pick["title"],
        "protein": pick["protein"],
        "prep_notes": pick["prep_notes"],
        "servings": pick.get("servings", 4) or 4,
        "score": 0,
        "pantry_matches": pantry_str,
        "tag_bonuses": "swapped",
    }
