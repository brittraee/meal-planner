"""Tests for ingredient parsing and normalization."""

from src.ingredients import (
    DEFAULT_PANTRY,
    get_default_qty,
    get_section,
    normalize,
    parse_ingredient,
)


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

    def test_garlic_cloves(self):
        assert normalize("garlic cloves") == "garlic"

    def test_extra_virgin_olive_oil(self):
        assert normalize("extra virgin olive oil") == "olive oil"

    def test_unsalted_butter(self):
        assert normalize("unsalted butter") == "butter"

    def test_kosher_salt(self):
        assert normalize("kosher salt") == "salt"

    def test_zucchinis_plural(self):
        assert normalize("zucchinis") == "zucchini"

    def test_mushrooms_plural(self):
        assert normalize("mushrooms") == "mushroom"

    def test_compound_salt_and_pepper(self):
        assert normalize("kosher salt and ground black pepper") == "salt"

    def test_plain_greek_yogurt(self):
        assert normalize("plain greek yogurt") == "greek yogurt"

    def test_yellow_onion(self):
        assert normalize("yellow onion") == "onion"


class TestDefaultPantry:
    def test_not_empty(self):
        assert len(DEFAULT_PANTRY) > 0

    def test_all_items_have_known_sections(self):
        for item in DEFAULT_PANTRY:
            assert get_section(item) != "other", f"{item} mapped to 'other'"


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


class TestGetDefaultQty:
    def test_exact_match_protein(self):
        qty, unit = get_default_qty("chicken breast")
        assert qty == 0.375
        assert unit == "lb"

    def test_exact_match_spice(self):
        qty, unit = get_default_qty("cumin")
        assert qty == 0.125
        assert unit == "tsp"

    def test_exact_match_canned(self):
        qty, unit = get_default_qty("black beans")
        assert qty == 0.25
        assert unit == "can"

    def test_exact_match_dairy(self):
        qty, unit = get_default_qty("cream cheese")
        assert qty == 1
        assert unit == "tbsp"

    def test_category_fallback_protein(self):
        """Protein in SECTION_MAP but not QUANTITY_DEFAULTS gets category default."""
        qty, unit = get_default_qty("turkey")
        assert qty == 0.375
        assert unit == "lb"

    def test_category_fallback_produce(self):
        qty, unit = get_default_qty("artichoke hearts")
        assert qty == 0.25
        assert unit == "whole"

    def test_no_match_returns_none(self):
        qty, unit = get_default_qty("unicorn tears")
        assert qty is None
        assert unit is None
