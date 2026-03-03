"""Parse Markdown recipe cards into Recipe objects."""

from __future__ import annotations

import re
from pathlib import Path

from src.ingredients import parse_ingredient
from src.models import Ingredient, Recipe


def parse_recipe(path: Path) -> Recipe:
    """Parse a single Markdown recipe card into a Recipe object.

    Expected format:
        ### Title
        **Main Ingredients:**
        - Ingredient 1
        - Ingredient 2
        **Quick Prep:**
        Description text.
        **Tags:** #tag1 #tag2
    """
    text = path.read_text(encoding="utf-8")
    lines = text.strip().splitlines()

    title = _extract_title(lines)
    ingredients = _extract_ingredients(lines)
    prep = _extract_prep(lines)
    tags = _extract_tags(lines)
    instructions = _extract_instructions(lines)

    return Recipe(
        title=title,
        filename=path.stem,
        ingredients=tuple(ingredients),
        prep=prep,
        tags=frozenset(tags),
        instructions=instructions,
    )


def parse_recipes(directory: Path) -> list[Recipe]:
    """Parse all recipe Markdown files in a directory.

    Skips README.md and _INDEX.md.
    """
    recipes: list[Recipe] = []
    skip = {"readme.md", "_index.md", "_template.md"}

    for path in sorted(directory.glob("*.md")):
        if path.name.lower() in skip:
            continue
        recipes.append(parse_recipe(path))

    return recipes


def _extract_title(lines: list[str]) -> str:
    """Extract the recipe title from a ### heading."""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("###"):
            return stripped.lstrip("#").strip()
    return "Untitled"


def _extract_ingredients(lines: list[str]) -> list[Ingredient]:
    """Extract ingredient lines between **Main Ingredients:** and **Quick Prep:**."""
    ingredients: list[Ingredient] = []
    in_section = False

    for line in lines:
        stripped = line.strip()

        if "**Main Ingredients:**" in stripped or "**Main Ingredients**" in stripped:
            in_section = True
            continue

        if in_section and ("**Quick Prep:**" in stripped or "**Quick Prep**" in stripped):
            break

        if in_section and stripped.startswith("- "):
            parsed = parse_ingredient(stripped)
            if parsed.name:
                ingredients.append(parsed)

    return ingredients


def _extract_prep(lines: list[str]) -> str:
    """Extract the quick prep description."""
    in_section = False
    prep_lines: list[str] = []

    for line in lines:
        stripped = line.strip()

        if "**Quick Prep:**" in stripped or "**Quick Prep**" in stripped:
            in_section = True
            # Check if there's text on the same line after the header
            after = re.sub(r"\*\*Quick Prep:?\*\*\s*", "", stripped).strip()
            if after:
                prep_lines.append(after)
            continue

        if in_section:
            if stripped.startswith("**Tags:**") or stripped.startswith("**Tags**"):
                break
            if stripped:
                prep_lines.append(stripped)

    return " ".join(prep_lines).strip()


def _extract_tags(lines: list[str]) -> set[str]:
    """Extract hashtags from the **Tags:** line."""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("**Tags:**") or stripped.startswith("**Tags**"):
            # Find all #word patterns
            return {m.group(1) for m in re.finditer(r"#(\w+)", stripped)}
    return set()


_INSTRUCTION_BOILERPLATE = {
    "did you love this recipe",
    "leftovers!",
    "let us know with a rating",
}


def _extract_instructions(lines: list[str]) -> str:
    """Pull instructions from the **Instructions:** section."""
    in_section = False
    instruction_lines: list[str] = []

    for line in lines:
        stripped = line.strip()

        if "**Instructions:**" in stripped or "**Instructions**" in stripped:
            in_section = True
            after = re.sub(r"\*\*Instructions:?\*\*\s*", "", stripped).strip()
            if after:
                instruction_lines.append(after)
            continue

        if in_section:
            if any(stripped.lower().startswith(b) for b in _INSTRUCTION_BOILERPLATE):
                break
            instruction_lines.append(line.rstrip())

    result = "\n".join(instruction_lines).strip()
    return result
