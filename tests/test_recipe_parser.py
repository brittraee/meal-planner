"""Tests for recipe Markdown parser."""

from src.recipe_parser import parse_recipe, parse_recipes


class TestParseRecipe:
    def test_extracts_title(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text(
            "### My Recipe\n**Main Ingredients:**\n- Chicken\n"
            "**Quick Prep:**\nCook it.\n**Tags:** #chicken"
        )
        recipe = parse_recipe(md)
        assert recipe.title == "My Recipe"

    def test_extracts_ingredients(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text(
            "### Test\n**Main Ingredients:**\n- Chicken\n- Rice\n"
            "**Quick Prep:**\nCook.\n**Tags:** #easy"
        )
        recipe = parse_recipe(md)
        assert len(recipe.ingredients) == 2

    def test_extracts_prep(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text(
            "### Test\n**Main Ingredients:**\n- Chicken\n"
            "**Quick Prep:**\nSlice and roast at 425.\n**Tags:** #chicken"
        )
        recipe = parse_recipe(md)
        assert "Slice and roast" in recipe.prep

    def test_extracts_tags(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text(
            "### Test\n**Main Ingredients:**\n- Chicken\n"
            "**Quick Prep:**\nCook.\n**Tags:** #chicken #easy #quick"
        )
        recipe = parse_recipe(md)
        assert recipe.tags == {"chicken", "easy", "quick"}

    def test_optional_ingredient(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text(
            "### Test\n**Main Ingredients:**\n- Chicken\n- Salsa (optional)\n"
            "**Quick Prep:**\nCook.\n**Tags:** #chicken"
        )
        recipe = parse_recipe(md)
        optional = [i for i in recipe.ingredients if i.optional]
        assert len(optional) == 1

    def test_alternative_ingredients(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text(
            "### Test\n**Main Ingredients:**\n- Butter or olive oil\n"
            "**Quick Prep:**\nCook.\n**Tags:** #easy"
        )
        recipe = parse_recipe(md)
        assert len(recipe.ingredients[0].alternatives) == 1

    def test_filename_becomes_recipe_filename(self, tmp_path):
        md = tmp_path / "01_Test_Recipe.md"
        md.write_text(
            "### Test\n**Main Ingredients:**\n- Chicken\n**Quick Prep:**\nCook.\n**Tags:** #chicken"
        )
        recipe = parse_recipe(md)
        assert recipe.filename == "01_Test_Recipe"

    def test_protein_from_tags(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text(
            "### Test\n**Main Ingredients:**\n- Steak\n"
            "**Quick Prep:**\nGrill.\n**Tags:** #steak #quick"
        )
        recipe = parse_recipe(md)
        assert recipe.protein.value == "beef"


class TestParseRecipes:
    def test_parses_all_real_recipes(self, meals_dir):
        if not meals_dir.exists():
            return
        recipes = parse_recipes(meals_dir)
        assert len(recipes) >= 68

    def test_skips_readme(self, tmp_path):
        (tmp_path / "README.md").write_text("# README")
        (tmp_path / "01_test.md").write_text(
            "### Test\n**Main Ingredients:**\n- X\n**Quick Prep:**\nY.\n**Tags:** #a"
        )
        recipes = parse_recipes(tmp_path)
        assert len(recipes) == 1

    def test_skips_index(self, tmp_path):
        (tmp_path / "_INDEX.md").write_text("# Index")
        (tmp_path / "01_test.md").write_text(
            "### Test\n**Main Ingredients:**\n- X\n**Quick Prep:**\nY.\n**Tags:** #a"
        )
        recipes = parse_recipes(tmp_path)
        assert len(recipes) == 1
