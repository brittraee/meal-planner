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
    "zucchinis": "zucchini",
    "mushrooms": "mushroom",
}

# Alias map: variant -> canonical name
ALIASES: dict[str, str] = {
    "chicken": "chicken breast",
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
    # Produce variants
    "garlic cloves": "garlic",
    "garlic clove": "garlic",
    "yellow onion": "onion",
    "white onion": "onion",
    "sweet onion": "onion",
    # Oil/fat variants
    "extra virgin olive oil": "olive oil",
    "extra-virgin olive oil": "olive oil",
    "evoo": "olive oil",
    "unsalted butter": "butter",
    "salted butter": "butter",
    # Seasoning variants
    "kosher salt": "salt",
    "sea salt": "salt",
    "ground black pepper": "black pepper",
    "freshly ground black pepper": "black pepper",
    "cracked black pepper": "black pepper",
    "ground pepper": "black pepper",
    # Dairy variants
    "plain greek yogurt": "greek yogurt",
    # Compound seasoning lines
    "kosher salt and ground black pepper": "salt",
    "salt and pepper": "salt",
    "salt and pepper to taste": "salt",
    "kosher salt and black pepper": "salt",
    "kosher salt and pepper": "salt",
    "fine sea salt": "salt",
    "fine sea salt and -ground black pepper": "salt",
    "fine sea salt and -cracked black pepper": "salt",
    "pinch of salt and black pepper": "salt",
    "half and half": "half and half",
    "half and half*": "half and half",
    "green onions": "green onion",
    "spring onions": "green onion",
    "scallions": "green onion",
    "salt and black pepper": "salt",
    # Dried herb variants
    "dried thyme": "thyme",
    "dried basil": "basil",
    "dried rosemary": "rosemary",
    "dried parsley": "parsley",
    "dried dill": "dill",
    "dried oregano": "oregano",
    # Common product descriptions
    "all-purpose flour": "flour",
    "all purpose flour": "flour",
    "ap flour": "flour",
    # Cheese variants
    "shredded cheese": "cheese",
    "shredded cheddar": "cheddar cheese",
    "provolone cheese": "cheese",
    "mozzarella cheese": "mozzarella",
    "american cheese": "cheese",
    "cheese slices": "cheese",
    "feta": "feta cheese",
    # Produce variants
    "red onions": "onion",
    "shallots": "shallot",
    "yellow pepper": "bell pepper",
    "red pepper": "bell pepper",
    "green bell pepper": "bell pepper",
    "courgettes": "zucchini",
    "aubergine": "eggplant",
    "baby potatoes": "potato",
    "basil leaves": "fresh basil",
    "broccoli florets": "broccoli",
    "cucumbers": "cucumber",
    "apples": "apple",
    # Oil variants
    "sesame seed oil": "sesame oil",
    "sunflower oil": "vegetable oil",
    "canola oil": "vegetable oil",
    # Protein variants
    "shredded pork": "pork",
    "cooked chicken": "chicken breast",
    "cooked steak": "steak",
    "sirloin steak": "steak",
    "beef fillet": "steak",
    "beef brisket": "steak",
    "chicken drumsticks": "chicken thigh",
    "cod fillet": "cod",
    "cod fillets": "cod",
    "breakfast sausage": "sausage",
    "cooked meatballs": "meatballs",
    "chorizo": "sausage",
    # Herb/spice variants
    "coriander": "cilantro",
    "smoked paprika": "paprika",
    "cayenne pepper": "chili powder",
    "ground ginger": "ginger",
    "red chilli": "red pepper flakes",
    "red chilli flakes": "red pepper flakes",
    "chilli flakes": "red pepper flakes",
    "chilli powder": "chili powder",
    "chilli": "chili powder",
    "cajun seasoning": "paprika",
    "cajun": "paprika",
    "onion salt": "onion powder",
    "allspice": "cinnamon",
    "bay leaves": "bay leaf",
    "cloves": "cinnamon",
    "chili seasoning": "chili powder",
    "pinch red pepper flakes": "red pepper flakes",
    # Sauce/condiment variants
    "tomato puree": "tomato paste",
    "chilli sauce": "hot sauce",
    "tomato ketchup": "ketchup",
    "barbeque sauce": "bbq sauce",
    "marinara sauce": "tomato sauce",
    "marinara": "tomato sauce",
    "dijon mustard": "mustard",
    "caesar dressing": "ranch dressing",
    "tzatziki sauce": "greek yogurt",
    "chipotle crema": "mexican crema",
    "chipotle chili paste": "chipotle seasoning",
    # Stock/broth variants
    "chicken stock": "chicken broth",
    "beef stock": "chicken broth",
    "vegetable stock": "vegetable broth",
    "beef broth": "chicken broth",
    # Canned/jarred variants
    "canned beans": "black beans",
    "refried beans": "black beans",
    "beans": "black beans",
    "chopped tomatoes": "diced tomatoes",
    "canned tomatoes": "diced tomatoes",
    "canned crushed tomatoes": "diced tomatoes",
    "canned artichokes": "artichoke hearts",
    # Grain/starch variants
    "cooked rice": "rice",
    "jasmine rice": "rice",
    "plain flour": "flour",
    "starch": "cornstarch",
    "caster sugar": "sugar",
    "flour tortillas": "tortilla",
    "hamburger buns": "slider bun",
    "sub rolls": "bread",
    "pita bread": "flatbread",
    "pita": "flatbread",
    # Misc
    "sesame seed": "sesame seeds",
    "sesame seeds": "sesame seeds",
    "red wine vinegar": "balsamic vinegar",
    "sake": "rice vinegar",
    "mirin": "rice vinegar",
    "cream of chicken": "chicken broth",
    "egg white": "egg",
    "optional: maple syrup": "maple syrup",
    "optional: sour cream": "sour cream",
    # Shorthand from markdown recipes
    "fajita": "fajita seasoning",
    "frozen": "frozen vegetables",
}

# Store section classification
SECTION_MAP: dict[str, str] = {
    # Protein
    "chicken breast": "protein",
    "chicken thigh": "protein",
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
    "shallot": "produce",
    "apple": "produce",
    "orange": "produce",
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
    # Pantry — herbs
    "thyme": "pantry",
    "basil": "pantry",
    "rosemary": "pantry",
    "parsley": "pantry",
    "dill": "pantry",
    "bay leaf": "pantry",
    "black pepper": "pantry",
    # Pantry — pasta & noodles
    "penne": "pantry",
    "ziti": "pantry",
    "rotini": "pantry",
    "fettuccine": "pantry",
    "egg noodles": "pantry",
    "vermicelli": "pantry",
    "wonton wrapper": "pantry",
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
    "puff pastry": "frozen",
    # Dairy — additional
    "half and half": "dairy",
}

# Per-serving quantity defaults: normalized_name → (qty_per_serving, unit)
# Stored quantities = qty_per_serving * base_servings (typically 4)
QUANTITY_DEFAULTS: dict[str, tuple[float, str]] = {
    # Proteins (per serving)
    "chicken breast": (0.375, "lb"),
    "chicken thigh": (0.375, "lb"),
    "steak": (0.375, "lb"),
    "ground beef": (0.375, "lb"),
    "ground turkey": (0.375, "lb"),
    "ground lamb": (0.375, "lb"),
    "pork": (0.375, "lb"),
    "pulled pork": (0.375, "lb"),
    "pork tenderloin": (0.375, "lb"),
    "pork chop": (1, "whole"),
    "shrimp": (0.375, "lb"),
    "salmon": (0.375, "lb"),
    "salmon fillet": (1, "fillet"),
    "cod": (1, "fillet"),
    "pollock": (1, "fillet"),
    "tuna": (0.375, "lb"),
    "fish": (1, "fillet"),
    "tofu": (0.25, "block"),
    "bacon": (0.5, "slice"),
    "sausage": (0.375, "lb"),
    "ham": (0.375, "lb"),
    "meatballs": (0.375, "lb"),
    "lamb": (0.375, "lb"),
    # Canned goods (per serving → 1 can for 4)
    "black beans": (0.25, "can"),
    "chickpeas": (0.25, "can"),
    "diced tomatoes": (0.25, "can"),
    "canned corn": (0.25, "can"),
    "coconut milk": (0.25, "can"),
    "enchilada sauce": (0.25, "can"),
    "tomato sauce": (0.25, "can"),
    "tomato paste": (0.5, "tbsp"),
    # Produce — large items (fraction of whole per serving)
    "onion": (0.25, "whole"),
    "red onion": (0.25, "whole"),
    "bell pepper": (0.25, "whole"),
    "zucchini": (0.25, "whole"),
    "eggplant": (0.25, "whole"),
    "potato": (0.5, "whole"),
    "sweet potato": (0.5, "whole"),
    "avocado": (0.25, "whole"),
    "lemon": (0.25, "whole"),
    "lime": (0.25, "whole"),
    "jalapeño": (0.25, "whole"),
    "tomato": (0.25, "whole"),
    "cucumber": (0.25, "whole"),
    "cauliflower": (0.25, "head"),
    "cabbage": (0.125, "head"),
    # Produce — leafy/chopped (per serving)
    "broccoli": (0.5, "cup"),
    "spinach": (0.5, "cup"),
    "kale": (0.5, "cup"),
    "lettuce": (0.5, "cup"),
    "carrot": (0.25, "whole"),
    "celery": (0.25, "stalk"),
    "mushroom": (0.25, "cup"),
    "green beans": (0.25, "cup"),
    "corn": (0.25, "cup"),
    "peas": (0.25, "cup"),
    "cherry tomatoes": (0.25, "cup"),
    "shallot": (0.25, "whole"),
    "apple": (0.5, "whole"),
    "orange": (0.5, "whole"),
    # Produce — herbs & aromatics
    "garlic": (0.5, "clove"),
    "ginger": (0.25, "tsp"),
    "cilantro": (0.5, "tbsp"),
    "fresh basil": (0.5, "tbsp"),
    "fresh parsley": (0.5, "tbsp"),
    "green onion": (0.5, "stalk"),
    # Dairy — cheese
    "cheese": (0.25, "cup"),
    "cheddar cheese": (0.25, "cup"),
    "monterey jack cheese": (0.25, "cup"),
    "parmesan cheese": (1, "tbsp"),
    "mozzarella": (0.25, "cup"),
    "feta cheese": (1, "tbsp"),
    "cream cheese": (1, "tbsp"),
    "ricotta": (0.25, "cup"),
    # Dairy — other
    "sour cream": (1, "tbsp"),
    "mexican crema": (1, "tbsp"),
    "greek yogurt": (1, "tbsp"),
    "heavy cream": (1, "tbsp"),
    "cream": (1, "tbsp"),
    "milk": (0.25, "cup"),
    "half and half": (1, "tbsp"),
    "butter": (0.5, "tbsp"),
    "egg": (1, "whole"),
    # Grains & starches
    "rice": (0.25, "cup"),
    "quinoa": (0.25, "cup"),
    "couscous": (0.25, "cup"),
    "pasta": (2, "oz"),
    "spaghetti": (2, "oz"),
    "penne": (2, "oz"),
    "ziti": (2, "oz"),
    "rotini": (2, "oz"),
    "fettuccine": (2, "oz"),
    "campanelle": (2, "oz"),
    "egg noodles": (2, "oz"),
    "noodles": (2, "oz"),
    "ramen noodles": (2, "oz"),
    "rice noodles": (2, "oz"),
    "vermicelli": (2, "oz"),
    "tortellini": (2, "oz"),
    "tortilla": (1, "whole"),
    "flatbread": (1, "whole"),
    "slider bun": (1, "whole"),
    "bread": (1, "slice"),
    "biscuits": (1, "whole"),
    "lentils": (0.25, "cup"),
    "wonton wrapper": (3, "whole"),
    # Oils
    "olive oil": (0.5, "tbsp"),
    "vegetable oil": (0.5, "tbsp"),
    "sesame oil": (0.25, "tsp"),
    "coconut oil": (0.5, "tbsp"),
    "oil": (0.5, "tbsp"),
    # Sauces & condiments
    "soy sauce": (0.75, "tbsp"),
    "fish sauce": (0.25, "tsp"),
    "oyster sauce": (0.5, "tbsp"),
    "teriyaki sauce": (1, "tbsp"),
    "sriracha": (0.25, "tsp"),
    "hot sauce": (0.25, "tsp"),
    "bbq sauce": (1, "tbsp"),
    "ketchup": (0.5, "tbsp"),
    "mustard": (0.25, "tsp"),
    "worcestershire sauce": (0.25, "tsp"),
    "pesto": (1, "tbsp"),
    "alfredo sauce": (0.25, "cup"),
    "salsa": (1, "tbsp"),
    "harissa paste": (0.5, "tsp"),
    "peanut butter": (1, "tbsp"),
    "honey": (0.5, "tbsp"),
    "maple syrup": (0.5, "tbsp"),
    "ranch dressing": (1, "tbsp"),
    "chicken broth": (0.25, "cup"),
    "vegetable broth": (0.25, "cup"),
    # Vinegars
    "rice vinegar": (0.5, "tsp"),
    "balsamic vinegar": (0.5, "tsp"),
    "white wine vinegar": (0.5, "tsp"),
    "apple cider vinegar": (0.5, "tsp"),
    # Baking & thickeners
    "flour": (1, "tbsp"),
    "cornstarch": (0.25, "tsp"),
    "sugar": (0.25, "tsp"),
    "brown sugar": (0.5, "tsp"),
    "panko breadcrumbs": (2, "tbsp"),
    "breadcrumbs": (2, "tbsp"),
    # Spices & seasonings (tiny per-serving amounts)
    "salt": (0.125, "tsp"),
    "pepper": (0.125, "tsp"),
    "black pepper": (0.125, "tsp"),
    "garlic powder": (0.125, "tsp"),
    "onion powder": (0.125, "tsp"),
    "cumin": (0.125, "tsp"),
    "paprika": (0.125, "tsp"),
    "chili powder": (0.125, "tsp"),
    "oregano": (0.125, "tsp"),
    "italian seasoning": (0.125, "tsp"),
    "curry powder": (0.125, "tsp"),
    "turmeric": (0.125, "tsp"),
    "cinnamon": (0.125, "tsp"),
    "red pepper flakes": (0.0625, "tsp"),
    "thyme": (0.125, "tsp"),
    "basil": (0.125, "tsp"),
    "rosemary": (0.125, "tsp"),
    "parsley": (0.125, "tsp"),
    "dill": (0.125, "tsp"),
    "bay leaf": (0.25, "whole"),
    "fajita seasoning": (0.25, "tbsp"),
    "taco seasoning": (0.25, "tbsp"),
    "ranch seasoning": (0.25, "tbsp"),
    "chipotle seasoning": (0.25, "tsp"),
    "brown gravy mix": (0.25, "tbsp"),
    # Nuts & seeds
    "peanuts": (1, "tbsp"),
    "cashews": (1, "tbsp"),
    "almonds": (1, "tbsp"),
    "sesame seeds": (0.25, "tsp"),
    # Frozen
    "frozen vegetables": (0.5, "cup"),
    "frozen corn": (0.25, "cup"),
    "frozen peas": (0.25, "cup"),
    "frozen shrimp": (0.375, "lb"),
    "hash browns": (0.5, "cup"),
    "cauliflower rice": (0.5, "cup"),
    "puff pastry": (0.25, "sheet"),
    # Misc
    "fritos": (0.25, "cup"),
    "dates": (2, "whole"),
    "dried dates": (2, "whole"),
}

# Category-level fallback defaults for items in SECTION_MAP but not in QUANTITY_DEFAULTS
_CATEGORY_DEFAULTS: dict[str, tuple[float, str]] = {
    "protein": (0.375, "lb"),
    "produce": (0.25, "whole"),
    "frozen": (0.5, "cup"),
}


def get_default_qty(normalized_name: str) -> tuple[float | None, str | None]:
    """Look up a per-serving default quantity for an ingredient.

    Returns (qty_per_serving, unit) or (None, None) if no default found.
    Priority: exact match in QUANTITY_DEFAULTS → category fallback via SECTION_MAP.
    """
    # Exact match
    if normalized_name in QUANTITY_DEFAULTS:
        return QUANTITY_DEFAULTS[normalized_name]

    # Category fallback via SECTION_MAP
    section = SECTION_MAP.get(normalized_name)
    if section:
        # Special cases within categories
        if section == "dairy" and "cheese" in normalized_name:
            return (0.25, "cup")
        if section == "dairy":
            return (1, "tbsp")
        if section == "pantry":
            # Check if it looks like a sauce/condiment or seasoning
            # (these are items in SECTION_MAP but not in QUANTITY_DEFAULTS)
            return (0.125, "tsp")
        if section in _CATEGORY_DEFAULTS:
            return _CATEGORY_DEFAULTS[section]

    return (None, None)


# Common staples to pre-populate on first run (~20 items across categories)
DEFAULT_PANTRY = [
    # Oils & fats
    "Olive oil", "Vegetable oil", "Butter",
    # Seasonings
    "Salt", "Pepper", "Garlic powder", "Onion powder",
    "Cumin", "Paprika", "Italian seasoning", "Red pepper flakes",
    # Baking
    "Flour", "Sugar", "Brown sugar",
    # Pantry staples
    "Rice", "Pasta", "Soy sauce", "Chicken broth",
    # Condiments
    "Honey", "Ketchup",
]


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
