# Meal Planner

Weekly meal planning app. Pick recipes, generate a plan, get a shopping list grouped by store section. Tracks your pantry so you're not buying stuff you already have.

Built with Streamlit, SQLite, and Pandas.

**[Live Demo](https://meal-planner.streamlit.app)** *(update URL after deploy)*

## Features

**Recipe Library** — 142 recipes, filterable by protein, cook time, and tags. Pin favorites to lock them into your next plan.

**Meal Planner** — Generates 3-7 day dinner plans. Scores recipes based on pantry matches, preferred tags, and cook time, then shuffles with weighted randomness so you don't eat the same thing every week. Enforces protein variety (no chicken three nights in a row).

**Shopping List** — Pulls ingredients from your plan, scales quantities by servings, groups by store section, and filters out anything already in your pantry.

**Add Recipe** — Paste a URL and the scraper pulls in title, ingredients, and image. Or add one by hand.

## Ingredient parsing

The hardest part of this project. Recipe websites format ingredients in every way imaginable — unicode fractions, brand names baked in, metric/imperial mixing, prep instructions stuffed into the ingredient name.

The parser runs each line through:

```text
raw text → unicode fractions → pricing removal → dual unit detection →
qty/unit/name split → brand stripping → descriptor removal → prep cleanup →
alias normalization → metric→imperial → DB
```

Some specifics:
- Strips 20+ grocery brand prefixes (Aldi store brands, Kraft, Barilla, etc.)
- Maps ~200 ingredients to store sections for shopping list grouping
- Normalizes variants ("extra virgin olive oil" → "olive oil", "kosher salt and ground black pepper" → "salt")
- Warns on import when an ingredient doesn't match anything known

## How the planner scores recipes

1. +3 for each ingredient you already have in your pantry
2. +3 for included ingredients you asked for
3. +2 for priority tags (like "quick" or "kid-friendly")
4. +1 for quick/easy, +1 for kid-friendly
5. Weighted random selection — higher scores are more likely, but not guaranteed
6. Greedy fill with protein-variety constraint

## Tech

Streamlit, SQLite (7 tables), Pandas, recipe-scrapers, pytest (146 tests), Ruff

## Project structure

```text
app.py                  # Entry point, nav, onboarding
pages/
  0_setup.py            # First-run defaults + pantry
  1_recipes.py          # Recipe library
  2_planner.py          # Plan generator
  3_shopping.py         # Shopping list
  4_pantry.py           # Pantry manager
  6_add_recipe.py       # URL import + manual entry
  7_preferences.py      # Settings + reset
src/
  database.py           # Schema + queries
  scraper.py            # URL scraping + ingredient parsing
  ingredients.py        # Normalization, aliases, sections
  planner.py            # Scoring + plan generation
  shopping.py           # List formatting
  models.py             # Dataclasses
  units.py              # Unit conversion
tests/                  # 146 tests
data/meals.db           # SQLite database
```

## Run locally

```bash
git clone https://github.com/brittraee/meal-planner.git && cd meal-planner
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
streamlit run app.py
```

## License

MIT
