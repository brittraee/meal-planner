"""Domain models: Recipe, Ingredient, Protein, Preferences, Pantry."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Protein(Enum):
    """Primary protein category inferred from recipe tags."""

    CHICKEN = "chicken"
    BEEF = "beef"
    PORK = "pork"
    SHRIMP = "shrimp"
    FISH = "fish"
    EGGS = "eggs"
    VEGETARIAN = "vegetarian"
    UNKNOWN = "unknown"


# --- Tag-to-enum mappings ---

TAG_TO_PROTEIN: dict[str, Protein] = {
    "chicken": Protein.CHICKEN,
    "beef": Protein.BEEF,
    "steak": Protein.BEEF,
    "meatballs": Protein.BEEF,
    "lamb": Protein.BEEF,
    "pork": Protein.PORK,
    "shrimp": Protein.SHRIMP,
    "seafood": Protein.SHRIMP,
    "fish": Protein.FISH,
    "salmon": Protein.FISH,
    "cod": Protein.FISH,
    "eggs": Protein.EGGS,
    "brinner": Protein.EGGS,
    "vegetarian": Protein.VEGETARIAN,
}


# --- Data models ---


@dataclass(frozen=True)
class Ingredient:
    """A single ingredient line from a recipe card."""

    name: str
    optional: bool = False
    alternatives: tuple[str, ...] = ()

    @property
    def normalized(self) -> str:
        return self.name.lower().strip()

    @property
    def all_names(self) -> tuple[str, ...]:
        """The primary name plus any alternatives."""
        return (self.name, *self.alternatives)


@dataclass(frozen=True)
class Recipe:
    """A parsed recipe card."""

    title: str
    filename: str
    ingredients: tuple[Ingredient, ...]
    prep: str
    tags: frozenset[str]

    @property
    def protein(self) -> Protein:
        for tag in self.tags:
            if tag in TAG_TO_PROTEIN:
                return TAG_TO_PROTEIN[tag]
        return Protein.UNKNOWN

    @property
    def number(self) -> int | None:
        """Extract recipe number from filename like '01_Sheet_Pan_...'."""
        parts = self.filename.split("_", 1)
        try:
            return int(parts[0])
        except (ValueError, IndexError):
            return None


@dataclass(frozen=True)
class Preferences:
    """User dietary preferences loaded from YAML."""

    people: str = ""
    style: str = "easy_weeknights"
    diet: str = "omnivore"
    exclude_ingredients: tuple[str, ...] = ()
    budget: str = "medium"
    allergies: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class Pantry:
    """Items on hand, loaded from YAML."""

    staples: tuple[str, ...] = ()
    fresh: tuple[str, ...] = ()

    @property
    def all_items(self) -> frozenset[str]:
        return frozenset((*self.staples, *self.fresh))
