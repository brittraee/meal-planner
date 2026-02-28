"""Shared display constants used by multiple pages."""

TAG_DISPLAY: dict[str, str] = {
    "comfortfood": "Comfort Food",
    "kidfriendly": "Kid Friendly",
    "batchcook": "Batch Cook",
    "onepan": "One Pan",
    "sheetpan": "Sheet Pan",
    "breakfast": "Breakfast",
    "sidedish": "Side Dish",
    "lowcarb": "Low Carb",
    "whole30": "Whole30",
    "bbq": "BBQ",
}

PROTEIN_SUBS: dict[str, list[str]] = {
    "beef": ["ground beef", "steak", "roast", "brisket"],
    "chicken": ["breast", "thigh", "drumstick", "whole chicken"],
    "pork": ["pork loin", "pork tenderloin", "pork shoulder"],
    "shrimp": ["large shrimp", "jumbo shrimp"],
    "turkey": ["ground turkey"],
}
