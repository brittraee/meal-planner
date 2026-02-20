"""Tests for SQLite database operations."""

from src.database import (
    add_pantry_item,
    create_meal_plan,
    delete_meal_plan,
    delete_pantry_item,
    get_all_recipes,
    get_meal_plans,
    get_pantry_items,
    get_planned_meals,
    get_recipe_count_by_protein,
    get_recipe_details,
    get_shopping_list,
    get_unique_proteins,
    get_unique_tags,
    get_user_settings,
    has_completed_onboarding,
    insert_recipe,
    insert_recipe_dict,
    save_user_settings,
    search_recipes,
)


class TestRecipeOperations:
    def test_insert_and_retrieve(self, db, sample_recipe):
        insert_recipe(db, sample_recipe)
        db.commit()
        recipes = get_all_recipes(db)
        assert len(recipes) == 1
        assert recipes[0]["title"] == "Test Chicken Tacos"

    def test_insert_idempotent(self, db, sample_recipe):
        insert_recipe(db, sample_recipe)
        insert_recipe(db, sample_recipe)
        db.commit()
        recipes = get_all_recipes(db)
        assert len(recipes) == 1

    def test_recipe_details_includes_ingredients(self, db, sample_recipe):
        insert_recipe(db, sample_recipe)
        db.commit()
        details = get_recipe_details(db, sample_recipe.filename)
        assert details is not None
        assert len(details["ingredients"]) == 4

    def test_recipe_details_includes_tags(self, db, sample_recipe):
        insert_recipe(db, sample_recipe)
        db.commit()
        details = get_recipe_details(db, sample_recipe.filename)
        assert "chicken" in details["tags"]

    def test_unique_tags(self, db_with_recipes):
        tags = get_unique_tags(db_with_recipes)
        assert "chicken" in tags
        assert "steak" in tags

    def test_unique_proteins(self, db_with_recipes):
        proteins = get_unique_proteins(db_with_recipes)
        assert "chicken" in proteins
        assert "beef" in proteins

    def test_insert_recipe_dict(self, db):
        data = {
            "id": "mealdb_52772",
            "title": "Teriyaki Chicken",
            "protein": "chicken",
            "servings": 4,
            "source_type": "mealdb",
            "ingredients": [
                {"name": "chicken breast", "qty": 2.0, "unit": "lb"},
                {"name": "soy sauce", "qty": 3.0, "unit": "tbsp"},
            ],
            "tags": ["chicken", "japanese"],
        }
        insert_recipe_dict(db, data)
        db.commit()
        details = get_recipe_details(db, "mealdb_52772")
        assert details is not None
        assert details["title"] == "Teriyaki Chicken"
        assert len(details["ingredients"]) == 2
        assert details["ingredients"][0]["qty"] == 2.0
        assert details["ingredients"][0]["unit"] == "lb"

    def test_recipe_count_by_protein(self, db_with_recipes):
        counts = get_recipe_count_by_protein(db_with_recipes)
        assert len(counts) > 0
        protein_map = {c["protein"]: c["count"] for c in counts}
        assert protein_map["chicken"] == 1


class TestSearchRecipes:
    def test_search_all(self, db_with_recipes):
        results = search_recipes(db_with_recipes)
        assert len(results) == 7

    def test_search_by_protein(self, db_with_recipes):
        results = search_recipes(db_with_recipes, protein="chicken")
        assert len(results) == 1
        assert results[0]["title"] == "Chicken Fajitas"

    def test_search_by_tag(self, db_with_recipes):
        results = search_recipes(db_with_recipes, tags=["sheetpan"])
        assert len(results) == 2

    def test_search_by_text(self, db_with_recipes):
        results = search_recipes(db_with_recipes, query="teriyaki")
        assert len(results) >= 1

    def test_search_combined_filters(self, db_with_recipes):
        results = search_recipes(db_with_recipes, protein="chicken", tags=["kidfriendly"])
        assert len(results) == 1


class TestMealPlanOperations:
    def test_create_and_retrieve_plan(self, db_with_recipes):
        meals = [
            (1, "Monday", "01_Chicken_Fajitas"),
            (2, "Tuesday", "12_Steak_Teriyaki"),
        ]
        plan_id = create_meal_plan(db_with_recipes, "Test Week", "2026-02-17", meals)
        assert plan_id is not None

        plans = get_meal_plans(db_with_recipes)
        assert len(plans) == 1
        assert plans[0]["meal_count"] == 2

    def test_get_planned_meals(self, db_with_recipes):
        meals = [
            (1, "Monday", "01_Chicken_Fajitas"),
            (2, "Tuesday", "12_Steak_Teriyaki"),
        ]
        plan_id = create_meal_plan(db_with_recipes, "Test Week", "2026-02-17", meals)
        planned = get_planned_meals(db_with_recipes, plan_id)
        assert len(planned) == 2
        assert planned[0]["title"] == "Chicken Fajitas"

    def test_delete_plan(self, db_with_recipes):
        meals = [(1, "Monday", "01_Chicken_Fajitas")]
        plan_id = create_meal_plan(db_with_recipes, "Test", "2026-02-17", meals)
        delete_meal_plan(db_with_recipes, plan_id)
        assert len(get_meal_plans(db_with_recipes)) == 0


class TestPantryOperations:
    def test_add_and_retrieve(self, db):
        add_pantry_item(db, "Olive Oil", "olive oil", "staples")
        items = get_pantry_items(db)
        assert len(items) == 1
        assert items[0]["name"] == "Olive Oil"

    def test_delete_item(self, db):
        item_id = add_pantry_item(db, "Rice", "rice", "staples")
        delete_pantry_item(db, item_id)
        assert len(get_pantry_items(db)) == 0


class TestShoppingList:
    def test_shopping_list_consolidates(self, db_with_recipes):
        meals = [
            (1, "Monday", "01_Chicken_Fajitas"),
            (2, "Tuesday", "32_Pork_Tacos"),
        ]
        plan_id = create_meal_plan(db_with_recipes, "Test", "2026-02-17", meals)
        items = get_shopping_list(db_with_recipes, plan_id)
        # Both recipes use tortilla — should appear once
        tortilla_items = [i for i in items if i["normalized_name"] == "tortilla"]
        assert len(tortilla_items) == 1
        # Should list both recipes
        assert "Chicken Fajitas" in tortilla_items[0]["needed_for"]
        assert "Pork Tacos" in tortilla_items[0]["needed_for"]

    def test_shopping_list_marks_pantry(self, db_with_recipes):
        add_pantry_item(db_with_recipes, "rice", "rice", "staples")
        meals = [(1, "Monday", "12_Steak_Teriyaki")]
        plan_id = create_meal_plan(db_with_recipes, "Test", "2026-02-17", meals)
        items = get_shopping_list(db_with_recipes, plan_id)
        rice = [i for i in items if i["normalized_name"] == "rice"]
        assert len(rice) == 1
        assert rice[0]["in_pantry"] == 1

    def test_shopping_list_excludes_optional(self, db_with_recipes):
        meals = [(1, "Monday", "24_Breakfast_Dinner")]
        plan_id = create_meal_plan(db_with_recipes, "Test", "2026-02-17", meals)
        items = get_shopping_list(db_with_recipes, plan_id)
        # Bacon is optional — should not appear
        bacon_items = [i for i in items if i["normalized_name"] == "bacon"]
        assert len(bacon_items) == 0


class TestUserSettings:
    def test_has_completed_onboarding_empty_db(self, db):
        assert has_completed_onboarding(db) is False

    def test_save_and_has_completed_onboarding(self, db):
        save_user_settings(db, "Brittney", 4, 5)
        assert has_completed_onboarding(db) is True

    def test_get_user_settings_before_save(self, db):
        assert get_user_settings(db) is None

    def test_save_and_get_user_settings(self, db):
        save_user_settings(db, "Brittney", 4, 5)
        settings = get_user_settings(db)
        assert settings is not None
        assert settings["name"] == "Brittney"
        assert settings["servings"] == 4
        assert settings["meals_per_week"] == 5
