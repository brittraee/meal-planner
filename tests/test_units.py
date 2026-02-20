"""Tests for unit normalization and quantity aggregation."""

from src.units import convert_and_sum, normalize_unit, parse_quantity


class TestNormalizeUnit:
    def test_tablespoons(self):
        assert normalize_unit("tablespoons") == "tbsp"

    def test_cups(self):
        assert normalize_unit("cups") == "cup"

    def test_lb(self):
        assert normalize_unit("pounds") == "lb"

    def test_none(self):
        assert normalize_unit(None) is None

    def test_empty(self):
        assert normalize_unit("") is None

    def test_passthrough(self):
        assert normalize_unit("handful") == "handful"


class TestParseQuantity:
    def test_cups(self):
        assert parse_quantity("2 cups") == (2.0, "cup")

    def test_fraction(self):
        qty, unit = parse_quantity("1/2 tsp")
        assert qty == 0.5
        assert unit == "tsp"

    def test_grams(self):
        assert parse_quantity("100g") == (100.0, "g")

    def test_empty(self):
        assert parse_quantity("") == (None, None)

    def test_unparseable(self):
        assert parse_quantity("to taste") == (None, None)


class TestConvertAndSum:
    def test_sums_same_unit(self):
        items = [
            {
                "normalized_name": "soy sauce",
                "display_name": "soy sauce",
                "needed_for": "Recipe A",
                "in_pantry": 0,
                "qty": 2.0,
                "unit": "tbsp",
            },
            {
                "normalized_name": "soy sauce",
                "display_name": "soy sauce",
                "needed_for": "Recipe B",
                "in_pantry": 0,
                "qty": 1.0,
                "unit": "tbsp",
            },
        ]
        result = convert_and_sum(items)
        assert len(result) == 1
        assert result[0]["qty"] == 3.0
        assert result[0]["unit"] == "tbsp"
        assert "Recipe A" in result[0]["needed_for"]
        assert "Recipe B" in result[0]["needed_for"]

    def test_no_qty_items_grouped(self):
        items = [
            {
                "normalized_name": "salt",
                "display_name": "salt",
                "needed_for": "Recipe A",
                "in_pantry": 0,
                "qty": None,
                "unit": None,
            },
            {
                "normalized_name": "salt",
                "display_name": "salt",
                "needed_for": "Recipe B",
                "in_pantry": 0,
                "qty": None,
                "unit": None,
            },
        ]
        result = convert_and_sum(items)
        assert len(result) == 1
        assert result[0]["qty"] is None
        assert "Recipe A" in result[0]["needed_for"]

    def test_different_items_stay_separate(self):
        items = [
            {
                "normalized_name": "chicken",
                "display_name": "chicken",
                "needed_for": "Recipe A",
                "in_pantry": 0,
                "qty": 2.0,
                "unit": "lb",
            },
            {
                "normalized_name": "rice",
                "display_name": "rice",
                "needed_for": "Recipe A",
                "in_pantry": 0,
                "qty": 1.0,
                "unit": "cup",
            },
        ]
        result = convert_and_sum(items)
        assert len(result) == 2

    def test_pantry_flag_preserved(self):
        items = [
            {
                "normalized_name": "olive oil",
                "display_name": "olive oil",
                "needed_for": "Recipe A",
                "in_pantry": 1,
                "qty": 2.0,
                "unit": "tbsp",
            },
        ]
        result = convert_and_sum(items)
        assert result[0]["in_pantry"] == 1
