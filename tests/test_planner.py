"""Tests for Pandas-based meal plan generation."""

import pandas as pd
import pytest

from src.planner import generate_plan


class TestGeneratePlan:
    def test_generates_correct_number_of_days(self, db_with_recipes):
        plan = generate_plan(db_with_recipes, days=5, seed=42)
        assert len(plan) == 5

    def test_returns_dataframe(self, db_with_recipes):
        plan = generate_plan(db_with_recipes, days=3, seed=42)
        assert isinstance(plan, pd.DataFrame)
        assert "title" in plan.columns
        assert "protein" in plan.columns
        assert "recipe_id" in plan.columns

    def test_has_day_labels(self, db_with_recipes):
        plan = generate_plan(db_with_recipes, days=3, seed=42, start_day="Monday")
        assert plan.iloc[0]["day_label"] == "Monday"
        assert plan.iloc[1]["day_label"] == "Tuesday"
        assert plan.iloc[2]["day_label"] == "Wednesday"

    def test_no_consecutive_same_protein(self, db_with_recipes):
        plan = generate_plan(db_with_recipes, days=5, seed=42)
        proteins = plan["protein"].tolist()
        for i in range(1, len(proteins)):
            if proteins[i] != "unknown" and proteins[i - 1] != "unknown":
                assert proteins[i] != proteins[i - 1], (
                    f"Same protein on days {i} and {i + 1}: {proteins[i]}"
                )

    def test_seed_reproducibility(self, db_with_recipes):
        plan1 = generate_plan(db_with_recipes, days=5, seed=42)
        plan2 = generate_plan(db_with_recipes, days=5, seed=42)
        assert plan1["recipe_id"].tolist() == plan2["recipe_id"].tolist()

    def test_vegetarian_filter(self, db_with_recipes):
        plan = generate_plan(db_with_recipes, days=3, diet="vegetarian", seed=42)
        for _, row in plan.iterrows():
            assert row["protein"] in ("vegetarian", "eggs", "unknown")

    def test_excluded_ingredients(self, db_with_recipes):
        plan = generate_plan(db_with_recipes, days=5, excluded_ingredients=["steak"], seed=42)
        assert "Steak Teriyaki Bowls" not in plan["title"].tolist()

    def test_empty_db_raises(self, db):
        with pytest.raises(ValueError, match="No recipes"):
            generate_plan(db, days=3)

    def test_start_day_wraps(self, db_with_recipes):
        plan = generate_plan(db_with_recipes, days=3, seed=42, start_day="Saturday")
        assert plan.iloc[0]["day_label"] == "Saturday"
        assert plan.iloc[1]["day_label"] == "Sunday"
        assert plan.iloc[2]["day_label"] == "Monday"

    def test_included_ingredients_prefer(self, db_with_recipes):
        plan = generate_plan(db_with_recipes, days=5, included_ingredients=["shrimp"], seed=42)
        titles = plan["title"].tolist()
        assert "Garlic Shrimp" in titles

    def test_included_ingredients_require(self, db_with_recipes):
        plan = generate_plan(
            db_with_recipes,
            days=1,
            included_ingredients=["steak"],
            require_included=True,
            seed=42,
        )
        assert plan.iloc[0]["title"] == "Steak Teriyaki Bowls"

    def test_included_ingredients_require_no_match(self, db_with_recipes):
        with pytest.raises(ValueError, match="No recipes match"):
            generate_plan(
                db_with_recipes,
                days=3,
                included_ingredients=["tofu"],
                require_included=True,
                seed=42,
            )
