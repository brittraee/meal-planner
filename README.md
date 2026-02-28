# Meal Planner

Weekly meal planning app built with Streamlit, SQLite, and Pandas. Generates dinner plans scored against pantry, builds grouped shopping lists, and handles recipe import from URLs with full ingredient normalization.

**[Live Demo](https://meal-planner-bre2026.streamlit.app)**

## Features

**Recipe Library** — 142 recipes, filterable by protein, cook time, and tags. Pin favorites to lock them into your next plan.

**Meal Planner** — Generates 3-7 day dinner plans. Scores recipes based on pantry matches, preferred tags, and cook time, then uses weighted random selection so you get a different plan each time. Enforces protein variety (no chicken three nights in a row).

**Shopping List** — Pulls ingredients from your plan, scales quantities by servings, groups by store section, and filters out anything already in your pantry.

**Add Recipe** — Paste a URL and the scraper pulls in title, ingredients, and image. Or add one by hand.

## Ingredient normalization

Recipe sites format ingredients inconsistently — unicode fractions, embedded brand names, metric/imperial mixing, prep instructions stuffed into the name. The normalization scripts (`src/scraper.py`, `src/ingredients.py`) handle parsing and are included so the pipeline stays consistent as recipes are added.

`ingredients.py` maintains a section map (~200 ingredients → store sections) and an alias table for common variants.

## How plan generation works

Recipes are scored based on what you have and what you like, then selected using weighted randomness so plans vary each time:

- +3 if you already have ingredients in your pantry
- +3 if the recipe matches an ingredient you requested
- +1 for quick/easy, +1 for kid-friendly
- +2 for your priority tags

Higher-scoring recipes are more likely to appear, but not guaranteed. The planner also avoids repeating the same protein on consecutive nights.

## Tech

**Stack:** Streamlit, SQLite (7 tables), Pandas, recipe-scrapers, TheMealDB API, Material Icons, custom CSS

**Dev tools:** pytest (146 tests), Ruff, Claude Code (Opus/Sonnet 4.6)

## Project structure

```text
app.py                  # Entry point, nav, onboarding
pages/
  0_setup.py            # First-run setup + pantry
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

Only four dependencies: `streamlit`, `pandas`, `requests`, `recipe-scrapers`.

```bash
git clone https://github.com/brittraee/meal-planner.git && cd meal-planner
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
streamlit run app.py
```

## Built by

[Brittney Erler-Rajek](https://github.com/brittraee)

AI-Disclosure: Self taught developer utilizing Claude Code (Opus 4.6) for boilerplate code gen, documentation lookup, brainstorming and learning.

## License

MIT
