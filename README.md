# Meal Planner

A meal planning app built with Streamlit, SQLite, and Pandas. Generates balanced weekly dinner plans from a curated recipe library, produces shopping lists grouped by store section, and tracks pantry inventory so you're not buying what you already have.

## What it does

- **Onboarding** — First-run wizard collects preferences and initial pantry inventory
- **Recipe Browser** — Search/filter ~150 recipes by protein, cook time, or tags; pin favorites to lock them into your plan
- **Meal Planner** — Scoring algorithm builds 3-7 day plans with protein variety, pantry-aware ranking, and tag priority options. Shows *why* each recipe was chosen (pantry matches, tag bonuses)
- **Shopping List** — Auto-consolidated from a meal plan, scaled by servings, grouped by store section, pantry items filtered out
- **Pantry** — Track what you have on hand; the planner and shopping list both use this
- **Add Recipe** — Import from URL or add manually

## Tech stack

| Layer | Tech |
| --- | --- |
| UI | Streamlit (multi-page, session state, forms) |
| Data | Pandas (scoring, weighted sampling, DataFrames) |
| Database | SQLite (7 tables, JOINs, aggregations) |
| Recipes | Markdown files (human-readable, parsed into structured data) |
| Tests | pytest (110 tests across 8 files) |
| Lint | Ruff |

## How the planner works

1. Load recipes, tags, and ingredients into DataFrames
2. Filter by diet, excluded/required ingredients
3. Score: +3 for pantry ingredient matches, +2 for priority tags, +1 for quick/easy, +1 for kid-friendly
4. Weighted shuffle — higher scores are more likely but everything has a chance
5. Fill days with greedy protein-variety selection (no back-to-back repeats)

## Data pipeline

```
Meals/*.md → recipe_parser.py → ingest.py → SQLite → Streamlit pages
```

Recipes are Markdown files. The parser extracts structured data. The ingest script loads it into SQLite. The database is disposable — delete it and re-run ingest to rebuild from source.

## Project structure

```
app.py                        # Entry point + onboarding
pages/
  1_recipes.py                # Recipe browser (card grid, filters, pin)
  2_planner.py                # Plan generator with scoring evidence
  3_shopping.py               # Shopping list
  4_pantry.py                 # Pantry manager
  6_add_recipe.py             # Add/import recipes
src/
  database.py                 # Schema, queries (7 tables)
  planner.py                  # Pandas plan generation + scoring
  recipe_parser.py            # Markdown → Recipe objects
  ingredients.py              # Normalization, aliases, store sections
  models.py                   # Dataclasses
  shopping.py                 # List consolidation
  scraper.py                  # URL recipe import
  units.py                    # Unit normalization
tests/                        # 110 tests
Meals/                        # ~150 curated recipe files
```

## Setup

```bash
git clone <repo-url> && cd meal_planner
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python scripts/ingest.py
streamlit run app.py
```

## Testing

```bash
pytest
```

## Data attribution

Recipe data was originally sourced from [TheMealDB](https://www.themealdb.com/) (free API), then converted to Markdown and curated down to ~150 recipes. The Markdown files in `Meals/` are the source of truth.

## License

MIT
