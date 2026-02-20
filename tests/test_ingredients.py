"""Tests for ingredient parsing and normalization."""

from src.ingredients import get_section, normalize, parse_ingredient


class TestParseIngredient:
    def test_simple_ingredient(self):
        ing = parse_ingredient("- Chicken breast")
        assert ing.name == "chicken breast"
        assert not ing.optional
        assert ing.alternatives == ()

    def test_optional_ingredient(self):
        ing = parse_ingredient("- Lemon (optional)")
        assert ing.name == "lemon"
        assert ing.optional

    def test_or_alternatives(self):
        ing = parse_ingredient("- Butter or olive oil")
        assert ing.name == "butter"
        assert ing.alternatives == ("olive oil",)
        assert not ing.optional

    def test_optional_with_alternatives(self):
        ing = parse_ingredient("- Sour cream or salsa (optional)")
        assert ing.name == "sour cream"
        assert ing.alternatives == ("salsa",)
        assert ing.optional

    def test_comma_separated_alternatives(self):
        ing = parse_ingredient("- Bacon, sausage, or ham (optional)")
        assert ing.name == "bacon"
        assert "sausage" in ing.alternatives
        assert "ham" in ing.alternatives
        assert ing.optional

    def test_parenthetical_description_stripped(self):
        ing = parse_ingredient("- Cheese (Monterey Jack)")
        assert "monterey" not in ing.name.lower() or ing.name == "monterey jack cheese"

    def test_parenthetical_quantity_stripped(self):
        ing = parse_ingredient("- Chicken breasts (2)")
        assert ing.name == "chicken breast"
        assert "2" not in ing.name

    def test_empty_line(self):
        ing = parse_ingredient("")
        assert ing.name == ""

    def test_rice_or_frozen_vegetables(self):
        ing = parse_ingredient("- Rice or frozen vegetables")
        assert ing.name == "rice"
        assert "frozen vegetables" in ing.alternatives

    def test_all_names_property(self):
        ing = parse_ingredient("- Butter or olive oil")
        assert ing.all_names == ("butter", "olive oil")


class TestNormalize:
    def test_lowercase(self):
        assert normalize("Chicken Breast") == "chicken breast"

    def test_strips_whitespace(self):
        assert normalize("  onion  ") == "onion"

    def test_alias_mapping(self):
        assert normalize("chicken breasts") == "chicken breast"
        assert normalize("bell peppers") == "bell pepper"

    def test_fajita_or_taco_alias(self):
        assert normalize("fajita or taco seasoning") == "fajita seasoning"

    def test_irregular_plural(self):
        assert normalize("potatoes") == "potato"

    def test_unknown_passthrough(self):
        assert normalize("something new") == "something new"


class TestGetSection:
    def test_protein(self):
        assert get_section("chicken breast") == "protein"
        assert get_section("shrimp") == "protein"

    def test_produce(self):
        assert get_section("bell pepper") == "produce"
        assert get_section("onion") == "produce"

    def test_dairy(self):
        assert get_section("cheddar cheese") == "dairy"
        assert get_section("butter") == "dairy"

    def test_pantry(self):
        assert get_section("rice") == "pantry"
        assert get_section("tortilla") == "pantry"

    def test_frozen(self):
        assert get_section("frozen vegetables") == "frozen"

    def test_unknown_section(self):
        assert get_section("dragon fruit") == "other"
