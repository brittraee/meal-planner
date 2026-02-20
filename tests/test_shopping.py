"""Tests for shopping list formatting."""

import json

from src.shopping import (
    format_shopping_json,
    format_shopping_markdown,
    format_shopping_text,
    group_by_section,
)


def _make_items():
    """Create sample shopping list items for testing."""
    return [
        {
            "normalized_name": "chicken breast",
            "needed_for": "Chicken Fajitas",
            "display_name": "chicken breast",
            "in_pantry": 0,
        },
        {
            "normalized_name": "bell pepper",
            "needed_for": "Chicken Fajitas",
            "display_name": "bell pepper",
            "in_pantry": 0,
        },
        {
            "normalized_name": "rice",
            "needed_for": "Steak Bowls",
            "display_name": "rice",
            "in_pantry": 1,
        },
    ]


class TestFormatMarkdown:
    def test_includes_need_items(self):
        md = format_shopping_markdown(_make_items())
        assert "chicken breast" in md
        assert "bell pepper" in md

    def test_marks_pantry_items(self):
        md = format_shopping_markdown(_make_items())
        assert "~~rice~~" in md

    def test_includes_recipe_names(self):
        md = format_shopping_markdown(_make_items())
        assert "Chicken Fajitas" in md

    def test_has_sections(self):
        md = format_shopping_markdown(_make_items())
        assert "## Protein" in md or "## Produce" in md


class TestFormatJson:
    def test_valid_json(self):
        result = format_shopping_json(_make_items())
        data = json.loads(result)
        assert "need" in data
        assert "in_pantry" in data

    def test_separates_need_and_pantry(self):
        data = json.loads(format_shopping_json(_make_items()))
        assert len(data["need"]) == 2
        assert len(data["in_pantry"]) == 1

    def test_includes_section_info(self):
        data = json.loads(format_shopping_json(_make_items()))
        sections = {item["section"] for item in data["need"]}
        assert len(sections) > 0


class TestGroupBySection:
    def test_groups_protein_and_produce(self):
        items = _make_items()
        need = [i for i in items if not i["in_pantry"]]
        sections = group_by_section(need)
        assert "chicken breast" in [i["normalized_name"] for i in sections["protein"]]
        assert "bell pepper" in [i["normalized_name"] for i in sections["produce"]]

    def test_unknown_items_go_to_other(self):
        items = [
            {
                "normalized_name": "unicorn dust",
                "needed_for": "Magic Soup",
                "display_name": "unicorn dust",
                "in_pantry": 0,
            }
        ]
        sections = group_by_section(items)
        assert "other" in sections


class TestFormatText:
    def test_includes_items(self):
        text = format_shopping_text(_make_items())
        assert "chicken breast" in text
        assert "bell pepper" in text

    def test_excludes_pantry_items(self):
        text = format_shopping_text(_make_items())
        assert "rice" not in text

    def test_has_section_headers(self):
        text = format_shopping_text(_make_items())
        assert "PROTEIN" in text or "PRODUCE" in text
