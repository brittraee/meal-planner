# Meal Planner

A full-stack meal planning app built with Streamlit, SQLite, and Pandas. Generates balanced weekly meal plans from a 250-recipe library, produces consolidated shopping lists, and tracks pantry inventory — with a first-run onboarding flow that personalizes the experience.

<!-- Screenshots: Replace these placeholders with actual screenshots -->
<!-- ![Onboarding](docs/screenshots/onboarding.png) -->
<!-- ![Recipe Browser](docs/screenshots/recipes.png) -->
<!-- ![Meal Plan](docs/screenshots/planner.png) -->
<!-- ![Shopping List](docs/screenshots/shopping.png) -->

## Features

- **First-Run Onboarding** — 3-step wizard collects name, preferences, and initial pantry inventory
- **Recipe Browser** — Search and filter 250 recipes by protein, tag, ingredient, or cook time
- **Meal Plan Generator** — Pandas-based scoring algorithm creates balanced 3-7 day plans with protein variety constraints
- **Shopping List** — Auto-consolidated from meal plans, scaled by servings, grouped by store section, with pantry subtraction
- **Pantry Tracker** — Track what's on hand; items are automatically excluded from shopping lists
- **History Dashboard** — View past plans and recipe usage frequency
- **Add Recipe** — Import from URL or add manually; supports TheMealDB and generic scraping

## Tech Stack

| Layer | Technology | Why |
| --- | --- | --- |
| UI | Streamlit | Multi-page app with session state, forms, and reactive widgets |
| Data Processing | Pandas | Recipe scoring, weighted sampling, DataFrame operations |
| Database | SQLite | Relational schema with JOINs, aggregations, migrations |
| Recipe Storage | Markdown | Human-readable source of truth, parseable into structured data |
| Testing | pytest | Unit tests for parser, planner, database, and ingredient normalization |
| Linting | Ruff | Fast Python linter/formatter |

## How It Works

### Data Pipeline

```
Meals/*.md  ──→  recipe_parser.py  ──→  ingest.py  ──→  SQLite DB
(source of truth)   (parse markdown)    (populate tables)     ↓
                                                    Streamlit pages
                                                    read from DB
```

Recipes are authored as Markdown files following a [template](Meals/_TEMPLATE.md). The parser extracts structured data (title, ingredients, tags, prep notes). The ingest script loads everything into SQLite. The database is disposable — delete it and re-run ingest to rebuild.

### Meal Plan Algorithm (`src/planner.py`)

1. **Load** recipes, tags, and ingredients from SQLite into Pandas DataFrames
2. **Filter** by diet mode, excluded/required ingredients
3. **Score** each recipe: +3 for using pantry ingredients, +1 for quick/easy tags, +1 for kid-friendly tags
4. **Weighted shuffle** — higher-scored recipes are more likely to be selected, but all recipes have a chance
5. **Variety selection** — greedy pick ensuring no consecutive days share the same protein

### Ingredient Normalization (`src/ingredients.py`)

Ingredients go through alias resolution, plural stripping, and section classification (protein/produce/dairy/pantry/frozen). This powers:

- Shopping list consolidation (e.g. "chicken breasts" and "chicken breast" merge)
- Pantry matching (your "olive oil" matches a recipe's "Olive Oil")
- Store section grouping on shopping lists

## Project Structure

```
├── app.py                    # Entry point: onboarding gate + navigation
├── pages/
│   ├── 1_recipes.py              # Recipe browser with search/filter
│   ├── 2_planner.py              # Meal plan generator
│   ├── 3_shopping.py             # Shopping list view
│   ├── 4_pantry.py               # Pantry inventory manager
│   ├── 5_history.py              # Plan history dashboard
│   └── 6_add_recipe.py           # Add/import recipes
├── src/
│   ├── database.py               # Schema, queries, migrations (7 tables)
│   ├── planner.py                # Pandas-based plan generation
│   ├── recipe_parser.py          # Markdown → Recipe objects
│   ├── ingredients.py            # Normalization, aliases, section mapping
│   ├── models.py                 # Dataclasses (Recipe, Ingredient, Protein)
│   ├── shopping.py               # Shopping list consolidation
│   ├── scraper.py                # URL recipe import
│   └── units.py                  # Unit normalization (tsp → teaspoon, etc.)
├── scripts/
│   ├── ingest.py                 # Markdown → SQLite import
│   ├── seed.py                   # TheMealDB API seeder
│   └── seed_to_markdown.py       # Seed JSON → Markdown conversion
├── tests/                    # pytest suite (8 test files)
├── Meals/                    # 250 recipe Markdown files
├── seed_data/                # TheMealDB JSON (595 recipes)
└── data/                     # SQLite database (generated)
```

## Setup

```bash
git clone <repo-url> && cd meal_planner
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python scripts/ingest.py      # populate database from Markdown recipes
streamlit run app.py           # open in browser
```

## Testing

```bash
pytest                         # run all tests
pytest tests/test_planner.py   # run specific test file
```

## Screenshots

> **TODO:** Add screenshots of each page. Suggested captures:
>
> 1. Onboarding Step 1 (Welcome + preferences form)
> 2. Onboarding Step 2 (Pantry picker with tabs)
> 3. Recipe browser with filters active
> 4. Generated meal plan with swap buttons
> 5. Shopping list grouped by store section
> 6. Pantry inventory page

Save screenshots to `docs/screenshots/` and uncomment the image tags at the top of this file.

## AI Usage

This project was developed with AI assistance (Claude). AI was used for:

- Seed data curation and Markdown recipe generation
- Boilerplate generation and refactoring
- Database schema iteration
- Code review

Core logic (planning algorithm, ingredient normalization, data pipeline design) was authored and understood by the developer. All code was reviewed and tested before inclusion.

## License

MIT
