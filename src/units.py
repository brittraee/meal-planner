"""Unit normalization, quantity parsing, and cross-unit conversion."""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

# Canonical unit aliases: variant → standard form
UNIT_ALIASES: dict[str, str] = {
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
    "milliliter": "ml",
    "milliliters": "ml",
    "liter": "L",
    "liters": "L",
    "litre": "L",
    "litres": "L",
    "clove": "clove",
    "cloves": "clove",
    "can": "can",
    "cans": "can",
    "slice": "slice",
    "slices": "slice",
    "piece": "piece",
    "pieces": "piece",
    "bunch": "bunch",
    "bunches": "bunch",
    "sprig": "sprig",
    "sprigs": "sprig",
}

# Units that can be added together (same dimension)
_CONVERTIBLE: dict[str, dict[str, float]] = {
    # Volume (base: tsp)
    "tsp": {"tsp": 1, "tbsp": 3, "cup": 48},
    "tbsp": {"tsp": 1 / 3, "tbsp": 1, "cup": 16},
    "cup": {"tsp": 1 / 48, "tbsp": 1 / 16, "cup": 1},
    # Weight (base: g)
    "g": {"g": 1, "kg": 1000, "oz": 28.3495, "lb": 453.592},
    "kg": {"g": 0.001, "kg": 1, "oz": 0.0283495, "lb": 0.453592},
    "oz": {"g": 1 / 28.3495, "kg": 1000 / 28.3495, "oz": 1, "lb": 16},
    "lb": {"g": 1 / 453.592, "kg": 1000 / 453.592, "oz": 1 / 16, "lb": 1},
    # Volume metric
    "ml": {"ml": 1, "L": 1000},
    "L": {"ml": 0.001, "L": 1},
}


def normalize_unit(unit: str | None) -> str | None:
    """Normalize a unit string to its canonical form."""
    if not unit:
        return None
    cleaned = unit.lower().strip().rstrip(".")
    return UNIT_ALIASES.get(cleaned, cleaned)


def parse_quantity(measure: str) -> tuple[float | None, str | None]:
    """Parse a measure string like '2 cups' into (qty, unit).

    Returns (None, None) for unparseable strings.
    """
    text = measure.strip()
    if not text:
        return None, None

    match = re.match(
        r"^\s*(\d+\s*/\s*\d+|\d+\.?\d*)\s*(.*)$",
        text,
    )
    if not match:
        return None, None

    raw_qty, raw_unit = match.group(1).strip(), match.group(2).strip()

    if "/" in raw_qty:
        num, denom = raw_qty.split("/")
        qty = float(num.strip()) / float(denom.strip())
    else:
        qty = float(raw_qty)

    unit = normalize_unit(raw_unit) if raw_unit else None
    return qty, unit


def _can_convert(unit_a: str, unit_b: str) -> bool:
    """Check if two units are in the same dimension and can be summed."""
    return unit_a in _CONVERTIBLE and unit_b in _CONVERTIBLE.get(unit_a, {})


def _convert(qty: float, from_unit: str, to_unit: str) -> float:
    """Convert qty from one unit to another within the same dimension."""
    if from_unit == to_unit:
        return qty
    factor = _CONVERTIBLE[to_unit][from_unit]
    return qty * factor


def convert_and_sum(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate shopping list items, summing compatible quantities.

    Used by shopping list formatters; see tests/test_units.py.

    Input items must have: normalized_name, qty (float|None), unit (str|None),
    needed_for, display_name, in_pantry.

    Same-name items with compatible units get their quantities summed.
    Items without quantities are grouped but show "—" for quantity.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        key = item["normalized_name"]
        groups.setdefault(key, []).append(item)

    result = []
    for name, group in groups.items():
        # Merge needed_for across all items in the group
        all_recipes = set()
        for g in group:
            for r in g["needed_for"].split(","):
                r = r.strip()
                if r:
                    all_recipes.add(r)

        in_pantry = any(g["in_pantry"] for g in group)

        # Try to sum quantities
        with_qty = [(g["qty"], normalize_unit(g.get("unit"))) for g in group if g.get("qty")]

        if not with_qty:
            # No quantities — keep as-is
            result.append({
                "normalized_name": name,
                "display_name": group[0]["display_name"],
                "needed_for": ", ".join(sorted(all_recipes)),
                "in_pantry": 1 if in_pantry else 0,
                "qty": None,
                "unit": None,
            })
            continue

        # Group by compatible unit dimension
        # Use the first item's unit as the target
        target_unit = with_qty[0][1]
        total = 0.0
        fallback = False

        for qty, unit in with_qty:
            if unit == target_unit:
                total += qty
            elif target_unit and unit and _can_convert(unit, target_unit):
                total += _convert(qty, unit, target_unit)
            else:
                # Incompatible units — can't aggregate, fall back
                fallback = True
                break

        if fallback:
            # Keep first item's display, concatenate recipes
            result.append({
                "normalized_name": name,
                "display_name": group[0]["display_name"],
                "needed_for": ", ".join(sorted(all_recipes)),
                "in_pantry": 1 if in_pantry else 0,
                "qty": None,
                "unit": None,
            })
        else:
            # Format the aggregated quantity
            display_qty = format_qty(total)
            unit_str = target_unit or ""
            display = f"{display_qty} {unit_str} {name}".strip()

            result.append({
                "normalized_name": name,
                "display_name": display,
                "needed_for": ", ".join(sorted(all_recipes)),
                "in_pantry": 1 if in_pantry else 0,
                "qty": total,
                "unit": target_unit,
            })

    return result


def format_qty(qty: float) -> str:
    """Format a quantity for display using fractions (e.g. 1/3, 1/2)."""
    if qty == int(qty):
        return str(int(qty))
    whole = int(qty)
    remainder = qty - whole
    frac = Fraction(remainder).limit_denominator(8)
    if frac.numerator == 0:
        return str(whole) if whole else "0"
    frac_str = f"{frac.numerator}/{frac.denominator}"
    return f"{whole} {frac_str}" if whole else frac_str
