"""Shopping list formatting and export.

SQL-based ingredient consolidation lives in database.py;
this module handles formatting for markdown and JSON export.
"""

from __future__ import annotations

import json
from typing import Any

from src.ingredients import SECTION_MAP

SECTION_ORDER = ("protein", "produce", "dairy", "pantry", "frozen", "other")


def enrich_shopping_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add store section to each shopping list item."""
    for item in items:
        item["section"] = SECTION_MAP.get(item["normalized_name"], "other")
    return items


def group_by_section(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group items by grocery store section, preserving SECTION_ORDER."""
    sections: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        section = SECTION_MAP.get(item["normalized_name"], "other")
        sections.setdefault(section, []).append(item)
    return sections


def format_shopping_markdown(items: list[dict[str, Any]]) -> str:
    """Format shopping list as Markdown for export."""
    need_items = [i for i in items if not i["in_pantry"]]
    have_items = [i for i in items if i["in_pantry"]]

    lines = ["# Shopping List\n"]

    if need_items:
        sections = group_by_section(need_items)
        for section in SECTION_ORDER:
            if section not in sections:
                continue
            lines.append(f"\n## {section.title()}\n")
            for item in sections[section]:
                recipes = item["needed_for"].replace(",", ", ")
                lines.append(f"- [ ] {item['display_name']} *(for: {recipes})*")

    if have_items:
        lines.append("\n## Already in Pantry\n")
        for item in have_items:
            lines.append(f"- ~~{item['display_name']}~~")

    return "\n".join(lines) + "\n"


def format_shopping_text(items: list[dict[str, Any]]) -> str:
    """Format shopping list as plain text for clipboard sharing."""
    need_items = [i for i in items if not i["in_pantry"]]
    lines: list[str] = []

    if need_items:
        sections = group_by_section(need_items)
        for section in SECTION_ORDER:
            if section not in sections:
                continue
            lines.append(f"{section.upper()}")
            for item in sections[section]:
                lines.append(f"  {item['display_name']}")
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def format_shopping_json(items: list[dict[str, Any]]) -> str:
    """Format shopping list as JSON for export."""
    return json.dumps(
        {
            "need": [
                {
                    "name": i["display_name"],
                    "normalized": i["normalized_name"],
                    "for_recipes": i["needed_for"].split(","),
                    "section": SECTION_MAP.get(i["normalized_name"], "other"),
                }
                for i in items
                if not i["in_pantry"]
            ],
            "in_pantry": [
                {"name": i["display_name"], "normalized": i["normalized_name"]}
                for i in items
                if i["in_pantry"]
            ],
        },
        indent=2,
    )
