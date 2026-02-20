"""Tests for TheMealDB seed script parsing."""

from scripts.seed import map_protein, parse_measure, transform_meal


class TestParseMeasure:
    def test_simple_cups(self):
        qty, unit = parse_measure("2 cups")
        assert qty == 2.0
        assert unit == "cup"

    def test_tablespoons(self):
        qty, unit = parse_measure("3  tablespoons")
        assert qty == 3.0
        assert unit == "tbsp"

    def test_grams_no_space(self):
        qty, unit = parse_measure("100g")
        assert qty == 100.0
        assert unit == "g"

    def test_fraction(self):
        qty, unit = parse_measure("1/2 tsp")
        assert qty == 0.5
        assert unit == "tsp"

    def test_empty(self):
        qty, unit = parse_measure("")
        assert qty is None
        assert unit is None

    def test_unparseable(self):
        qty, unit = parse_measure("pinch")
        assert qty is None
        assert unit is None

    def test_decimal(self):
        qty, unit = parse_measure("1.5 lbs")
        assert qty == 1.5
        assert unit == "lb"


class TestMapProtein:
    def test_chicken(self):
        assert map_protein("Chicken") == "chicken"

    def test_seafood(self):
        assert map_protein("Seafood") == "fish"

    def test_lamb_maps_to_beef(self):
        assert map_protein("Lamb") == "beef"

    def test_unknown_category(self):
        assert map_protein("Miscellaneous") == "unknown"

    def test_vegetarian(self):
        assert map_protein("Vegetarian") == "vegetarian"


class TestTransformMeal:
    def test_basic_transform(self):
        meal = {
            "idMeal": "52772",
            "strMeal": "Teriyaki Chicken",
            "strCategory": "Chicken",
            "strArea": "Japanese",
            "strInstructions": "Cook the chicken.",
            "strMealThumb": "https://example.com/img.jpg",
            "strTags": "MainMeal",
            "strSource": "https://example.com",
            "strIngredient1": "chicken breast",
            "strMeasure1": "2 lbs",
            "strIngredient2": "soy sauce",
            "strMeasure2": "3 tablespoons",
            "strIngredient3": "",
            "strMeasure3": "",
        }
        result = transform_meal(meal)

        assert result["id"] == "mealdb_52772"
        assert result["title"] == "Teriyaki Chicken"
        assert result["protein"] == "chicken"
        assert result["source_type"] == "mealdb"
        assert len(result["ingredients"]) == 2
        assert result["ingredients"][0]["qty"] == 2.0
        assert result["ingredients"][0]["unit"] == "lb"
        assert result["ingredients"][1]["normalized_name"] == "soy sauce"
        assert "chicken" in result["tags"]
        assert "japanese" in result["tags"]
        assert "mainmeal" in result["tags"]

    def test_null_fields_handled(self):
        meal = {
            "idMeal": "99999",
            "strMeal": "Mystery Meal",
            "strCategory": None,
            "strArea": None,
            "strInstructions": None,
            "strMealThumb": None,
            "strTags": None,
            "strSource": None,
        }
        result = transform_meal(meal)
        assert result["id"] == "mealdb_99999"
        assert result["protein"] == "unknown"
        assert result["ingredients"] == []
        assert result["tags"] == []
