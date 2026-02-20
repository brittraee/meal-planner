"""Ingredient parsing, normalization, and store-section classification."""

from __future__ import annotations

import re

from src.models import Ingredient

# Parenthetical patterns to strip (quantities, descriptions, but NOT "optional")
_PAREN_RE = re.compile(r"\s*\([^)]*\)\s*")
_OPTIONAL_RE = re.compile(r"\s*\(optional\)\s*", re.IGNORECASE)

# Common plural -> singular mappings that simple 's' stripping won't handle
_IRREGULAR_PLURALS: dict[str, str] = {
    "potatoes": "potato",
    "tomatoes": "tomato",
    "tortillas": "tortilla",
    "hash browns": "hash browns",
    "green beans": "green beans",
    "black beans": "black beans",
    "biscuits": "biscuits",
    "enchiladas": "enchiladas",
    "dates": "dates",
    "noodles": "noodles",
    "meatballs": "meatballs",
}

# Alias map: variant -> canonical name
ALIASES: dict[str, str] = {
    "chicken breasts": "chicken breast",
    "chicken thighs": "chicken thigh",
    "bell peppers": "bell pepper",
    "onions": "onion",
    "eggs": "egg",
    "carrots": "carrot",
    "lemons": "lemon",
    "limes": "lime",
    "peppers": "pepper",
    "sliders buns": "slider bun",
    "slider buns": "slider bun",
    "flatbreads": "flatbread",
    "quesadillas": "quesadilla",
    "diced tomatoes (canned)": "diced tomatoes",
    "black beans (canned)": "black beans",
    "canned black beans": "black beans",
    "canned diced tomatoes": "diced tomatoes",
    "frozen vegetables": "frozen vegetables",
    "frozen veggies": "frozen vegetables",
    "steam-in-bag veggies": "frozen vegetables",
    "mexican crema": "mexican crema",
    "crema": "mexican crema",
    "sour cream": "sour cream",
    "monterey jack": "monterey jack cheese",
    "cheese (monterey jack)": "monterey jack cheese",
    "cheddar": "cheddar cheese",
    "parmesan": "parmesan cheese",
    "parm": "parmesan cheese",
    "olive oil": "olive oil",
    "fajita seasoning": "fajita seasoning",
    "taco seasoning": "taco seasoning",
    "fajita or taco seasoning": "fajita seasoning",
    "ranch seasoning": "ranch seasoning",
    "ranch dressing": "ranch dressing",
    "brown gravy mix or pan gravy": "brown gravy mix",
    "chipotle chili paste or seasoning": "chipotle seasoning",
}

# Store section classification
SECTION_MAP: dict[str, str] = {
    # Protein
    "chicken breast": "protein",
    "chicken thigh": "protein",
    "chicken": "protein",
    "steak": "protein",
    "ground beef": "protein",
    "ground turkey": "protein",
    "turkey": "protein",
    "lamb": "protein",
    "ground lamb": "protein",
    "pork": "protein",
    "pulled pork": "protein",
    "pork tenderloin": "protein",
    "pork chop": "protein",
    "shrimp": "protein",
    "salmon": "protein",
    "salmon fillet": "protein",
    "cod": "protein",
    "pollock": "protein",
    "tuna": "protein",
    "fish": "protein",
    "tofu": "protein",
    "bacon": "protein",
    "sausage": "protein",
    "ham": "protein",
    "meatballs": "protein",
    # Produce
    "bell pepper": "produce",
    "onion": "produce",
    "red onion": "produce",
    "garlic": "produce",
    "ginger": "produce",
    "broccoli": "produce",
    "spinach": "produce",
    "kale": "produce",
    "carrot": "produce",
    "celery": "produce",
    "potato": "produce",
    "sweet potato": "produce",
    "cabbage": "produce",
    "lettuce": "produce",
    "tomato": "produce",
    "cherry tomatoes": "produce",
    "lime": "produce",
    "lemon": "produce",
    "cilantro": "produce",
    "fresh basil": "produce",
    "fresh parsley": "produce",
    "avocado": "produce",
    "jalapeño": "produce",
    "green onion": "produce",
    "mushroom": "produce",
    "cucumber": "produce",
    "eggplant": "produce",
    "green beans": "produce",
    "corn": "produce",
    "zucchini": "produce",
    "cauliflower": "produce",
    "artichoke hearts": "produce",
    "peas": "produce",
    "snow peas": "produce",
    "bean sprouts": "produce",
    "bok choy": "produce",
    "dates": "produce",
    "dried dates": "produce",
    # Dairy
    "cheese": "dairy",
    "cheddar cheese": "dairy",
    "monterey jack cheese": "dairy",
    "parmesan cheese": "dairy",
    "mozzarella": "dairy",
    "feta cheese": "dairy",
    "ricotta": "dairy",
    "cream cheese": "dairy",
    "sour cream": "dairy",
    "mexican crema": "dairy",
    "greek yogurt": "dairy",
    "heavy cream": "dairy",
    "cream": "dairy",
    "milk": "dairy",
    "butter": "dairy",
    "egg": "dairy",
    # Pantry — staples
    "flour": "pantry",
    "sugar": "pantry",
    "brown sugar": "pantry",
    "cornstarch": "pantry",
    "baking powder": "pantry",
    "rice": "pantry",
    "pasta": "pantry",
    "spaghetti": "pantry",
    "bread": "pantry",
    "tortilla": "pantry",
    "tortillas": "pantry",
    "noodles": "pantry",
    "ramen noodles": "pantry",
    "rice noodles": "pantry",
    "tortellini": "pantry",
    "campanelle": "pantry",
    "couscous": "pantry",
    "quinoa": "pantry",
    "lentils": "pantry",
    "flatbread": "pantry",
    "slider bun": "pantry",
    "biscuits": "pantry",
    "panko breadcrumbs": "pantry",
    "breadcrumbs": "pantry",
    "fritos": "pantry",
    # Pantry — canned / jarred
    "black beans": "pantry",
    "chickpeas": "pantry",
    "canned corn": "pantry",
    "diced tomatoes": "pantry",
    "tomato paste": "pantry",
    "tomato sauce": "pantry",
    "coconut milk": "pantry",
    "chicken broth": "pantry",
    "vegetable broth": "pantry",
    # Pantry — oils & vinegars
    "olive oil": "pantry",
    "vegetable oil": "pantry",
    "sesame oil": "pantry",
    "coconut oil": "pantry",
    "oil": "pantry",
    "rice vinegar": "pantry",
    "balsamic vinegar": "pantry",
    "white wine vinegar": "pantry",
    "apple cider vinegar": "pantry",
    # Pantry — sauces & condiments
    "soy sauce": "pantry",
    "fish sauce": "pantry",
    "oyster sauce": "pantry",
    "teriyaki sauce": "pantry",
    "sriracha": "pantry",
    "hot sauce": "pantry",
    "bbq sauce": "pantry",
    "ketchup": "pantry",
    "mustard": "pantry",
    "worcestershire sauce": "pantry",
    "pesto": "pantry",
    "alfredo sauce": "pantry",
    "enchilada sauce": "pantry",
    "harissa paste": "pantry",
    "salsa": "pantry",
    "peanut butter": "pantry",
    "honey": "pantry",
    "maple syrup": "pantry",
    # Pantry — spices & seasonings
    "salt": "pantry",
    "pepper": "pantry",
    "garlic powder": "pantry",
    "onion powder": "pantry",
    "cumin": "pantry",
    "paprika": "pantry",
    "chili powder": "pantry",
    "oregano": "pantry",
    "italian seasoning": "pantry",
    "curry powder": "pantry",
    "turmeric": "pantry",
    "cinnamon": "pantry",
    "red pepper flakes": "pantry",
    "fajita seasoning": "pantry",
    "taco seasoning": "pantry",
    "ranch seasoning": "pantry",
    "chipotle seasoning": "pantry",
    "brown gravy mix": "pantry",
    # Pantry — nuts & seeds
    "peanuts": "pantry",
    "cashews": "pantry",
    "almonds": "pantry",
    "sesame seeds": "pantry",
    # Frozen
    "frozen vegetables": "frozen",
    "frozen corn": "frozen",
    "frozen peas": "frozen",
    "frozen shrimp": "frozen",
    "hash browns": "frozen",
    "cauliflower rice": "frozen",
}


def normalize(name: str) -> str:
    """Normalize an ingredient name to a canonical form."""
    text = name.lower().strip()
    # Apply alias map first
    if text in ALIASES:
        return ALIASES[text]
    # Try irregular plurals
    if text in _IRREGULAR_PLURALS:
        return _IRREGULAR_PLURALS[text]
    # Simple plural stripping (only for words ending in 's' but not 'ss')
    if text.endswith("s") and not text.endswith("ss") and len(text) > 3:
        singular = text[:-1]
        if singular in ALIASES:
            return ALIASES[singular]
    return text


def get_section(name: str) -> str:
    """Look up the store section for an ingredient."""
    normalized = normalize(name)
    return SECTION_MAP.get(normalized, "other")


def get_ingredients_by_section() -> dict[str, list[str]]:
    """Invert SECTION_MAP into section -> list of display-ready ingredient names.

    Returns e.g. {"Protein": ["Chicken Breast", ...], "Produce": [...], ...}
    """
    sections: dict[str, list[str]] = {}
    for ingredient, section in SECTION_MAP.items():
        label = section.title()
        sections.setdefault(label, []).append(ingredient.title())
    for items in sections.values():
        items.sort()
    return sections


def parse_ingredient(line: str) -> Ingredient:
    """Parse a single ingredient line from a recipe card.

    Handles patterns like:
    - "Chicken breast"
    - "Lemon (optional)"
    - "Butter or olive oil"
    - "Bacon, sausage, or ham (optional)"
    - "Cheese (Monterey Jack)"
    """
    text = line.strip().lstrip("- ").strip()
    if not text:
        return Ingredient(name="", optional=False)

    # Check for (optional) and remove it
    optional = bool(_OPTIONAL_RE.search(text))
    text = _OPTIONAL_RE.sub("", text).strip()

    # Strip other parenthetical notes (quantities, descriptions)
    text = _PAREN_RE.sub("", text).strip()

    # Split on " or " to find alternatives
    # Handle "X, Y, or Z" pattern
    alternatives: list[str] = []
    if ", " in text and " or " in text:
        # "Bacon, sausage, or ham" -> split on comma and "or"
        parts = re.split(r",\s*(?:or\s+)?|\s+or\s+", text)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) > 1:
            primary = normalize(parts[0])
            alternatives = [normalize(p) for p in parts[1:]]
            return Ingredient(
                name=primary,
                optional=optional,
                alternatives=tuple(alternatives),
            )
    elif " or " in text:
        parts = text.split(" or ", 1)
        primary = normalize(parts[0].strip())
        alt = normalize(parts[1].strip())
        return Ingredient(name=primary, optional=optional, alternatives=(alt,))

    return Ingredient(name=normalize(text), optional=optional)
