"""Tests for URL recipe scraper."""

from unittest.mock import MagicMock, patch

from src.scraper import _parse_qty_unit, _slugify, scrape_recipe


class TestParseQtyUnit:
    def test_cups(self):
        assert _parse_qty_unit("2 cups") == (2.0, "cup")

    def test_tablespoons(self):
        assert _parse_qty_unit("3 tablespoons") == (3.0, "tbsp")

    def test_fraction(self):
        qty, unit = _parse_qty_unit("1/2 teaspoon")
        assert qty == 0.5
        assert unit == "tsp"

    def test_no_match(self):
        assert _parse_qty_unit("a pinch of salt") == (None, None)

    def test_empty(self):
        assert _parse_qty_unit("") == (None, None)


class TestSlugify:
    def test_basic(self):
        assert _slugify("Chicken Parmesan") == "url_chicken_parmesan"

    def test_special_chars(self):
        assert _slugify("Mom's Best Mac & Cheese!") == "url_mom_s_best_mac_cheese"


class TestScrapeRecipe:
    @patch("src.scraper.scrape_me")
    def test_scrape_returns_dict(self, mock_scrape_me):
        mock = MagicMock()
        mock.title.return_value = "Test Recipe"
        mock.ingredients.return_value = ["2 cups flour", "1 tsp salt"]
        mock.category.return_value = "dinner"
        mock.yields.return_value = "4 servings"
        mock.image.return_value = "https://example.com/img.jpg"
        mock.instructions.return_value = "Mix and bake."
        mock_scrape_me.return_value = mock

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

    @patch("src.scraper.scrape_me")
    def test_handles_missing_optional_fields(self, mock_scrape_me):
        mock = MagicMock()
        mock.title.return_value = "Simple Dish"
        mock.ingredients.return_value = ["salt"]
        mock.category.side_effect = NotImplementedError
        mock.yields.side_effect = NotImplementedError
        mock.image.side_effect = NotImplementedError
        mock.instructions.return_value = ""
        mock_scrape_me.return_value = mock

        result = scrape_recipe("https://example.com/simple")

        assert result["title"] == "Simple Dish"
        assert result["servings"] == 4  # default
        assert result["image_url"] == ""
        assert result["tags"] == []
