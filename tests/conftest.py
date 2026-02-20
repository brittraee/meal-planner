"""Shared test fixtures with in-memory SQLite."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.database import init_db, insert_recipe
from src.models import Ingredient, Pantry, Preferences, Recipe


@pytest.fixture()
def meals_dir() -> Path:
    """Path to the real Meals/ directory."""
    return Path(__file__).parent.parent / "Meals"


@pytest.fixture()
def db() -> sqlite3.Connection:
    """In-memory SQLite database with schema initialized."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)
    return conn


@pytest.fixture()
def db_with_recipes(db, sample_recipes) -> sqlite3.Connection:
    """Database pre-populated with sample recipes."""
    for recipe in sample_recipes:
        insert_recipe(db, recipe)
    db.commit()
    return db


@pytest.fixture()
def sample_recipe() -> Recipe:
    """A minimal recipe for unit tests."""
    return Recipe(
        title="Test Chicken Tacos",
        filename="99_Test_Chicken_Tacos",
        ingredients=(
            Ingredient(name="chicken breast"),
            Ingredient(name="tortilla"),
            Ingredient(name="salsa", optional=True),
            Ingredient(name="sour cream", optional=False, alternatives=("greek yogurt",)),
        ),
        prep="Cook chicken, assemble tacos.",
        tags=frozenset({"chicken", "tacos", "kidfriendly"}),
    )


@pytest.fixture()
def sample_recipes() -> list[Recipe]:
    """A set of diverse recipes for planner and database tests."""
    return [
        Recipe(
            title="Chicken Fajitas",
            filename="01_Chicken_Fajitas",
            ingredients=(
                Ingredient(name="chicken breast"),
                Ingredient(name="bell pepper"),
                Ingredient(name="onion"),
                Ingredient(name="fajita seasoning"),
                Ingredient(name="tortilla"),
            ),
            prep="Slice and roast.",
            tags=frozenset({"chicken", "fajitas", "sheetpan", "kidfriendly"}),
        ),
        Recipe(
            title="Steak Teriyaki Bowls",
            filename="12_Steak_Teriyaki",
            ingredients=(
                Ingredient(name="steak"),
                Ingredient(name="broccoli"),
                Ingredient(name="rice"),
                Ingredient(name="teriyaki sauce"),
            ),
            prep="Cook steak and serve over rice.",
            tags=frozenset({"steak", "bowl", "asianfusion"}),
        ),
        Recipe(
            title="Pork Tacos",
            filename="32_Pork_Tacos",
            ingredients=(
                Ingredient(name="pork"),
                Ingredient(name="tortilla"),
                Ingredient(name="cabbage"),
                Ingredient(name="lime"),
            ),
            prep="Cook pork, make slaw.",
            tags=frozenset({"pork", "tacos", "quickmeal"}),
        ),
        Recipe(
            title="Garlic Shrimp",
            filename="37_Garlic_Shrimp",
            ingredients=(
                Ingredient(name="shrimp"),
                Ingredient(name="garlic"),
                Ingredient(name="butter"),
                Ingredient(name="rice"),
            ),
            prep="Saute shrimp in garlic butter.",
            tags=frozenset({"shrimp", "quickmeal", "lowspoon"}),
        ),
        Recipe(
            title="Black Bean Enchiladas",
            filename="55_Black_Bean_Enchiladas",
            ingredients=(
                Ingredient(name="black beans"),
                Ingredient(name="rice"),
                Ingredient(name="tortilla"),
                Ingredient(name="cheese"),
                Ingredient(name="enchilada sauce"),
            ),
            prep="Roll and bake.",
            tags=frozenset({"vegetarian", "enchiladas", "comfortfood"}),
        ),
        Recipe(
            title="Salmon with Veggies",
            filename="52_Salmon_Veggies",
            ingredients=(
                Ingredient(name="salmon fillet"),
                Ingredient(name="potato"),
                Ingredient(name="carrot"),
                Ingredient(name="harissa paste"),
            ),
            prep="Roast veggies, sear salmon.",
            tags=frozenset({"salmon", "harissa", "sheetpan"}),
        ),
        Recipe(
            title="Breakfast for Dinner",
            filename="24_Breakfast_Dinner",
            ingredients=(
                Ingredient(name="egg"),
                Ingredient(name="potato", alternatives=("hash browns",)),
                Ingredient(name="cheese"),
                Ingredient(name="bacon", optional=True),
            ),
            prep="Scramble eggs, cook potatoes.",
            tags=frozenset({"brinner", "eggs", "comfortfood"}),
        ),
    ]


@pytest.fixture()
def sample_preferences() -> Preferences:
    """Preferences matching the example YAML."""
    return Preferences(
        people="2 adults + 1 child",
        style="easy_weeknights",
        diet="omnivore",
        exclude_ingredients=("mushrooms", "olives"),
        budget="medium",
        allergies=(),
        notes="Aim for 30-min dinners.",
    )


@pytest.fixture()
def sample_pantry() -> Pantry:
    """Pantry matching the example YAML."""
    return Pantry(
        staples=(
            "olive oil",
            "salt",
            "pepper",
            "rice",
            "pasta",
            "black beans",
            "diced tomatoes",
            "onion",
            "garlic",
            "tortilla",
            "egg",
            "cheddar cheese",
            "milk",
            "peanut butter",
        ),
        fresh=("chicken breast", "ground turkey", "spinach", "bell pepper"),
    )
