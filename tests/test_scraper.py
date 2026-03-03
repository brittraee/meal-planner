"""Tests for URL recipe scraper."""

from unittest.mock import MagicMock, patch

from src.scraper import _slugify, parse_ingredient_line, scrape_recipe


class TestParseIngredientLine:
    def test_cups(self):
        qty, unit, name = parse_ingredient_line("2 cups flour")
        assert qty == 2.0
        assert unit == "cup"
        assert name == "flour"

    def test_tablespoons(self):
        qty, unit, name = parse_ingredient_line("3 tablespoons olive oil")
        assert qty == 3.0
        assert unit == "tbsp"
        assert name == "olive oil"

    def test_fraction(self):
        qty, unit, name = parse_ingredient_line("1/2 teaspoon salt")
        assert qty == 0.5
        assert unit == "tsp"
        assert name == "salt"

    def test_mixed_fraction(self):
        qty, unit, name = parse_ingredient_line("1 1/2 pounds ground beef")
        assert qty == 1.5
        assert unit == "lb"
        assert name == "ground beef"

    def test_range(self):
        qty, _unit, name = parse_ingredient_line("8 to 12 flour tortillas")
        assert qty == 10.0
        assert "tortilla" in name

    def test_range_with_unit(self):
        qty, unit, name = parse_ingredient_line("1 to 2 cups rice")
        assert qty == 1.5
        assert unit == "cup"
        assert name == "rice"

    def test_mixed_fraction_range(self):
        qty, unit, name = parse_ingredient_line(
            "1 1/4 to 1 1/2 pounds skinless, boneless chicken breasts"
        )
        assert 1.3 < qty < 1.4
        assert unit == "lb"
        assert name == "chicken breast"

    def test_no_quantity(self):
        qty, unit, _name = parse_ingredient_line("salt and pepper to taste")
        assert qty is None
        assert unit is None

    def test_empty(self):
        qty, _unit, _name = parse_ingredient_line("")
        assert qty is None

    def test_descriptors_stripped(self):
        qty, unit, name = parse_ingredient_line("2 cups shredded cheddar cheese")
        assert qty == 2.0
        assert unit == "cup"
        assert name == "cheddar cheese"

    def test_parenthetical_stripped(self):
        qty, unit, name = parse_ingredient_line("1 (15 oz) can black beans")
        assert qty == 1.0
        assert unit == "can"
        assert name == "black beans"

    def test_size_word_skipped(self):
        qty, unit, name = parse_ingredient_line("1 large onion")
        assert qty == 1.0
        assert unit is None
        assert name == "onion"

    def test_unicode_fraction(self):
        qty, unit, name = parse_ingredient_line("\u00bd cup flour")
        assert qty == 0.5
        assert unit == "cup"
        assert name == "flour"

    def test_mixed_unicode_fraction(self):
        qty, unit, name = parse_ingredient_line("1\u00bd lbs chicken")
        assert qty == 1.5
        assert unit == "lb"
        assert name == "chicken breast"

    def test_pricing_stripped(self):
        qty, unit, name = parse_ingredient_line("\u00bc cup olive oil ($0.88)")
        assert qty == 0.25
        assert unit == "cup"
        assert name == "olive oil"

    def test_dual_unit_prefers_imperial(self):
        qty, unit, name = parse_ingredient_line("1 kg / 2 lb chicken")
        assert qty == 2.0
        assert unit == "lb"
        assert name == "chicken breast"

    def test_metric_conversion_grams(self):
        qty, unit, name = parse_ingredient_line("400 g spaghetti")
        assert 14.0 < qty < 14.2
        assert unit == "oz"
        assert name == "spaghetti"

    def test_metric_conversion_ml(self):
        qty, unit, name = parse_ingredient_line("237 ml water")
        assert 0.9 < qty < 1.1
        assert unit == "cup"
        assert name == "water"

    def test_unclosed_paren_stripped(self):
        _qty, _unit, name = parse_ingredient_line("1 jalapeño ( into thin rings")
        assert "(" not in name
        assert "ring" not in name

    def test_unclosed_paren_prep_instruction(self):
        _qty, _unit, name = parse_ingredient_line("1 can black beans (drained and rinsed")
        assert "(" not in name
        assert "drained" not in name

    def test_brand_name_stripped(self):
        qty, unit, name = parse_ingredient_line("1 cup Baker's Corner all-purpose flour")
        assert qty == 1.0
        assert unit == "cup"
        assert name == "flour"

    def test_aldi_brand_stripped(self):
        _qty, _unit, name = parse_ingredient_line("2 tbsp Stonemill dried basil")
        assert "stonemill" not in name.lower()
        assert "basil" in name

    def test_brand_countryside_creamery(self):
        _qty, unit, name = parse_ingredient_line("1 cup Countryside Creamery half and half")
        assert "countryside" not in name.lower()
        assert "half and half" in name


class TestSlugify:
    def test_basic(self):
        assert _slugify("Chicken Parmesan") == "url_chicken_parmesan"

    def test_special_chars(self):
        assert _slugify("Mom's Best Mac & Cheese!") == "url_mom_s_best_mac_cheese"


class TestScrapeRecipe:
    @patch("src.scraper._fetch_html")
    @patch("src.scraper.scrape_html")
    def test_scrape_returns_dict(self, mock_scrape_html, mock_fetch):
        mock_fetch.return_value = "<html></html>"
        mock = MagicMock()
        mock.title.return_value = "Test Recipe"
        mock.ingredients.return_value = ["2 cups flour", "1 tsp salt"]
        mock.category.return_value = "dinner"
        mock.yields.return_value = "4 servings"
        mock.image.return_value = "https://example.com/img.jpg"
        mock.instructions.return_value = "Mix and bake."
        mock_scrape_html.return_value = mock

        result = scrape_recipe("https://example.com/recipe")

        assert result["title"] == "Test Recipe"
        assert result["id"] == "url_test_recipe"
        assert result["source_type"] == "url"
        assert result["source_url"] == "https://example.com/recipe"
        assert result["servings"] == 4
        assert len(result["ingredients"]) == 2
        assert result["ingredients"][0]["raw_text"] == "2 cups flour"
        assert result["ingredients"][0]["qty"] == 2.0
        assert result["ingredients"][0]["unit"] == "cup"
        assert "dinner" in result["tags"]

    @patch("src.scraper._fetch_html")
    @patch("src.scraper.scrape_html")
    def test_handles_missing_optional_fields(self, mock_scrape_html, mock_fetch):
        mock_fetch.return_value = "<html></html>"
        mock = MagicMock()
        mock.title.return_value = "Simple Dish"
        mock.ingredients.return_value = ["salt"]
        mock.category.side_effect = NotImplementedError
        mock.yields.side_effect = NotImplementedError
        mock.image.side_effect = NotImplementedError
        mock.instructions.return_value = ""
        mock_scrape_html.return_value = mock

        result = scrape_recipe("https://example.com/simple")

        assert result["title"] == "Simple Dish"
        assert result["servings"] == 4  # default
        assert result["image_url"] == ""
        assert result["tags"] == []
