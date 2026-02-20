"""Integration tests: end-to-end data flow through parse → DB → plan → shopping list."""

from __future__ import annotations

from src.database import (
    add_pantry_item,
    create_meal_plan,
    get_shopping_list,
    insert_recipe,
    insert_recipe_dict,
    save_user_settings,
)
from src.planner import generate_plan
from src.recipe_parser import parse_recipe


class TestFullPipeline:
    """Parse a real markdown file → insert → plan → shopping list."""

    def test_full_pipeline_parse_to_shopping_list(self, db, meals_dir):
        # Parse a real recipe from the Meals/ directory
        recipe_path = meals_dir / "01_Sheet_Pan_Chicken_Fajitas.md"
        if not recipe_path.exists():
            # Fall back to any available recipe
            md_files = sorted(meals_dir.glob("*.md"))
            md_files = [f for f in md_files if f.name.lower() not in {"readme.md", "_template.md"}]
            assert md_files, "No recipe files found in Meals/"
            recipe_path = md_files[0]

        recipe = parse_recipe(recipe_path)
        assert recipe.title
        assert len(recipe.ingredients) > 0

        # Insert into DB
        insert_recipe(db, recipe)
        db.commit()

        # Generate a 1-day plan using the DB
        plan_df = generate_plan(db, days=1, seed=42)
        assert len(plan_df) == 1

        # Save the plan and get the shopping list
        meals = [
            (
                int(row["day"]),
                row["day_label"],
                row["recipe_id"],
            )
            for _, row in plan_df.iterrows()
        ]
        plan_id = create_meal_plan(db, "Integration Test", "2026-02-23", meals)
        items = get_shopping_list(db, plan_id)
        assert len(items) > 0
        # Every item should have a normalized_name and a recipe reference
        for item in items:
            assert item["normalized_name"]
            assert item["needed_for"]


class TestScrapeToplan:
    """Insert a recipe via insert_recipe_dict (mocked scraper output) → plan → shopping list."""

    def test_scrape_to_plan(self, db):
        scraped = {
            "id": "url_test_pasta",
            "title": "Test Pasta",
            "protein": "unknown",
            "prep_notes": "",
            "servings": 4,
            "source_url": "https://example.com/pasta",
            "source_type": "url",
            "instructions": "Boil pasta. Add sauce.",
            "image_url": "",
            "ingredients": [
                {
                    "raw_text": "1 lb pasta",
                    "normalized_name": "pasta",
                    "is_optional": False,
                    "qty": 1.0,
                    "unit": "lb",
                },
                {
                    "raw_text": "2 cups marinara sauce",
                    "normalized_name": "marinara sauce",
                    "is_optional": False,
                    "qty": 2.0,
                    "unit": "cup",
                },
            ],
            "tags": ["pasta", "quickmeal"],
        }
        insert_recipe_dict(db, scraped)
        db.commit()

        plan_df = generate_plan(db, days=1, seed=42)
        assert len(plan_df) == 1
        assert plan_df.iloc[0]["title"] == "Test Pasta"

        meals = [(1, "Monday", "url_test_pasta")]
        plan_id = create_meal_plan(db, "Scrape Test", "2026-02-23", meals)
        items = get_shopping_list(db, plan_id)
        names = {i["normalized_name"] for i in items}
        assert "pasta" in names
        assert "marinara sauce" in names


class TestPlannerEdgeCases:
    """Planner handles degenerate recipe pools gracefully."""

    def test_planner_all_same_protein(self, db):
        for i in range(5):
            insert_recipe_dict(db, {
                "id": f"chicken_{i}",
                "title": f"Chicken Dish {i}",
                "protein": "chicken",
                "ingredients": [
                    {"name": "chicken breast", "qty": 1.0, "unit": "lb"},
                ],
                "tags": ["chicken"],
            })
        db.commit()

        plan_df = generate_plan(db, days=5, seed=42)
        assert len(plan_df) == 5
        assert all(plan_df["protein"] == "chicken")


class TestOnboardingToPantrySubtraction:
    """Full onboarding → pantry → plan → shopping list flow."""

    def test_onboarding_to_pantry_subtraction(self, db, sample_recipes):
        # Onboard: save user settings
        save_user_settings(db, "Brittney", 4, 5)

        # Insert recipes
        for recipe in sample_recipes:
            insert_recipe(db, recipe)
        db.commit()

        # Add pantry items (rice and tortilla are used by multiple sample recipes)
        add_pantry_item(db, "Rice", "rice", "staples")
        add_pantry_item(db, "Tortilla", "tortilla", "staples")

        # Generate plan and create it
        plan_df = generate_plan(db, days=3, seed=42)
        assert len(plan_df) == 3

        meals = [
            (int(row["day"]), row["day_label"], row["recipe_id"])
            for _, row in plan_df.iterrows()
        ]
        plan_id = create_meal_plan(db, "Pantry Test", "2026-02-23", meals)
        items = get_shopping_list(db, plan_id)

        # If any planned recipe uses rice or tortilla, it should be marked in_pantry
        rice = [i for i in items if i["normalized_name"] == "rice"]
        tortilla = [i for i in items if i["normalized_name"] == "tortilla"]

        for pantry_item in rice + tortilla:
            assert pantry_item["in_pantry"] == 1, (
                f"{pantry_item['normalized_name']} should be marked as in_pantry"
            )
