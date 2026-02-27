#!/usr/bin/env python3
"""Convert curated seed recipes to Markdown files in Meals/.

Picks ~200 well-known US lunch/dinner recipes from mealdb_recipes.json
and writes them in the same format the recipe parser expects.

Usage:
    python scripts/seed_to_markdown.py            # generate markdown files
    python scripts/seed_to_markdown.py --dry-run   # preview without writing
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SEED_FILE = Path(__file__).parent.parent / "seed_data" / "mealdb_recipes.json"
MEALS_DIR = Path(__file__).parent.parent / "Meals"
START_NUMBER = 70  # existing files go up to 69

# ---------------------------------------------------------------------------
# Curated recipe list: well-known US lunch/dinner mains
# ---------------------------------------------------------------------------
INCLUDE_TITLES: set[str] = {
    # American classics
    "BBQ Pork Sloppy Joes",
    "Beef Brisket Pot Roast",
    "Big Mac",
    "Braised Beef Chilli",
    "Chick-Fil-A Sandwich",
    "Chicken Enchilada Casserole",
    "Chicken Fajita Mac and Cheese",
    "Clam chowder",
    "Corned Beef and Cabbage",
    "Corned Beef Hash",
    "Creamy Tomato Soup",
    "Crock Pot Chicken Baked Tacos",
    "French Onion Chicken with Roasted Carrots & Mashed Potatoes",
    "French Onion Soup",
    "Grilled Mac and Cheese Sandwich",
    "Honey Balsamic Chicken with Crispy Broccoli & Potatoes",
    "Kentucky Fried Chicken",
    "Smoky Lentil Chili with Squash",
    "Soy-Glazed Meatloaves with Wasabi Mashed Potatoes & Roasted Carrots",
    "Split Pea Soup",
    "Stuffed Bell Peppers with Quinoa and Black Beans",
    "Teriyaki Chicken Casserole",
    "Turkey Meatloaf",
    "Vegetarian Chilli",
    # Chinese-American
    "Beef and Broccoli Stir-Fry",
    "Beef Lo Mein",
    "Chicken Fried Rice",
    "Chinese Orange Chicken",
    "Chinese Tomato Egg Stir Fry",
    "Egg Drop Soup",
    "Egg Foo Young",
    "General Tsos Chicken",
    "Hot and Sour Soup",
    "Kung Pao Chicken",
    "Kung Po Prawns",
    "Ma Po Tofu",
    "Shrimp Chow Fun",
    "Shrimp With Snow Peas",
    "Singapore Noodles with Shrimp",
    "Sweet and Sour Chicken",
    "Sweet and Sour Pork",
    "Szechuan Beef",
    "Wontons",
    "Napa Cabbage with Dried Shrimp",
    "Sichuan Eggplant",
    # Italian-American
    "Chicken Alfredo Primavera",
    "Chilli prawn linguine",
    "Fettuccine Alfredo",
    "Lasagne",
    "Mediterranean Pasta Salad",
    "Rigatoni with fennel sausage sauce",
    "Spaghetti alla Carbonara",
    "Spaghetti Bolognese",
    "Spicy Arrabiata Penne",
    "Spinach & Ricotta Cannelloni",
    "Squash linguine",
    "Vegan Lasagna",
    "Mushroom & Chestnut Rotolo",
    "Osso Buco alla Milanese",
    "Venetian Duck Ragu",
    # Mexican / Tex-Mex
    "Cajun spiced fish tacos",
    "Chickpea Fajitas",
    # French
    "Beef Bourguignon",
    "Beef Wellington",
    "Coq au vin",
    "Duck Confit",
    "French Lentils With Garlic and Thyme",
    "French Omelette",
    "Fish Stew with Rouille",
    "Ratatouille",
    # Thai
    "Drunken noodles (pad kee mao)",
    "Pad See Ew",
    "Pad Thai",
    "Thai Green Curry",
    "Thai beef stir-fry",
    "Thai curry noodle soup",
    "Thai green chicken soup",
    "Thai pork & peanut curry",
    "Thai prawn curry",
    "Thai fried rice with prawns & peas",
    "Thai drumsticks",
    "Thai pumpkin soup",
    "Thai rice noodle salad",
    "Tom kha gai",
    "Tom yum soup with prawns",
    "Panang chicken curry (kaeng panang gai)",
    "Massaman Beef curry",
    "Spicy Thai prawn noodles",
    # Japanese
    "Chicken Karaage",
    "Honey Teriyaki Salmon",
    "Japanese Katsudon",
    "Katsu Chicken curry",
    "Ramen Noodles with Boiled Egg",
    "Sushi",
    "Tonkatsu pork",
    "Yaki Udon",
    # Indian
    "Chicken Handi",
    "Dal fry",
    "Kidney Bean Curry",
    "Lamb Biryani",
    "Lamb Rogan josh",
    "Matar Paneer",
    "Nutty Chicken Curry",
    "Tandoori chicken",
    # Vietnamese
    "Beef Banh Mi Bowls with Sriracha Mayo, Carrot & Pickled Cucumber",
    "Beef pho",
    "Turkey Bánh mì",
    "Vegan banh mi",
    "Vietnamese Grilled Pork (bun-thit-nuong)",
    "Vietnamese chicken salad",
    "Vietnamese pork salad",
    "Vietnamese-style caramel pork",
    # Middle Eastern / Mediterranean
    "Chicken Shawarma with homemade garlic herb yoghurt sauce",
    "Falafel",
    "Falafel Pita Sandwich with Tahini Sauce",
    "Shawarma",
    "Shakshuka",
    "Vegetarian Shakshuka",
    "Lamb and Lemon Souvlaki",
    "Lamb Tzatziki Burgers",
    "Moussaka",
    "Gigantes Plaki",
    "Chicken Quinoa Greek Salad",
    # Spanish
    "Paella",
    "Spanish Chicken",
    "Chicken & chorizo rice pot",
    "Chickpea, chorizo & spinach stew",
    # Jamaican / Caribbean
    "Brown Stew Chicken",
    "Jamaican Curry Chicken Recipe",
    "Jamaican Curry Shrimp Recipe",
    "Jamaican Pepper Shrimp",
    "Jerk chicken with rice & peas",
    # Korean / Other Asian
    "Beef Rendang",
    "Laksa King Prawn Noodles",
    "Stir-fried chicken with chillies & basil",
    # Other well-known
    "Aussie Burgers",
    "Bean & Sausage Hotpot",
    "Beef Empanadas",
    "Beef stroganoff",
    "Beef Sunday Roast",
    "Chicken & mushroom Hotpot",
    "Chicken Basquaise",
    "Chicken Couscous",
    "Chicken Congee",
    "Chicken Marengo",
    "Chicken Parmentier",
    "Chicken wings with cumin, lemon & garlic",
    "Crispy Eggplant",
    "Crispy Sausages and Greens",
    "Cumberland Pie",
    "Empanadas",
    "Escovitch Fish",
    "Irish stew",
    "kofta burgers",
    "Lamb Tagine",
    "Lamb & apricot meatballs",
    "Noodle bowl salad",
    "Piri-piri chicken and slaw",
    "Potato Gratin with Chicken",
    "Poutine",
    "Prawn stir-fry",
    "Red curry chicken kebabs",
    "Roasted chicken with creamy walnut sauce",
    "Salmon Prawn Risotto",
    "Salmon noodle soup",
    "Salmon noodle wraps",
    "Salt & pepper squid",
    "Skillet Apple Pork Chops with Roasted Sweet Potatoes & Zucchini",
    "Smoky chicken skewers",
    "Spiced smoky barbecued chicken",
    "Steak Diane",
    "Sticky Chicken",
    "Tahini Lentils",
    "Tofu, greens & cashew stir-fry",
    "Tuna Nicoise",
    "Vegetarian Casserole",
    "Golabki (cabbage roll)",
    "Baked salmon with fennel & tomatoes",
    "Barbecue pork buns",
    "Easy Spanish chicken",
    "Kedgeree",
    "Sesame Cucumber Salad",
}


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------

# Tags to skip in output (too vague, not useful for filtering)
SKIP_TAGS = {
    "miscellaneous", "mainmeal", "meat", "pulse", "baking", "calorific",
    "expensive", "cheap", "heavy", "light", "unhealthy", "greasy",
    "highfat", "lowcalorie", "lowcarbs", "warm", "warming", "fresh",
    "sour", "strongflavor", "hangoverfood", "dinnerparty", "datenight",
    "party", "celebration", "speciality", "onthego", "savoury", "savory",
}

# Map seed proteins to tag-friendly names
PROTEIN_TAG = {
    "chicken": "chicken",
    "beef": "beef",
    "pork": "pork",
    "fish": "seafood",
    "eggs": "eggs",
    "vegetarian": "vegetarian",
    "unknown": None,
}


def clean_title_for_filename(title: str) -> str:
    """Convert title to a filesystem-safe name."""
    # Remove parenthetical, special chars
    clean = re.sub(r"[^\w\s-]", "", title)
    clean = re.sub(r"\s+", "_", clean.strip())
    return clean


def extract_prep_summary(instructions: str) -> str:
    """Extract a 1-2 sentence prep summary from full instructions."""
    if not instructions:
        return "Follow recipe instructions."

    # Clean up the text
    text = instructions.replace("\r\n", "\n").replace("\r", "\n")

    # Remove step headers: "step 1", "STEP 1", "Step 1:", standalone numbers
    text = re.sub(r"^(step\s*\d+:?\s*)", "", text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r"^\d+[\.\)]\s*", "", text, flags=re.MULTILINE)

    # Split into paragraphs, filter empties and very short ones
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 10]
    if not paragraphs:
        # Try splitting on single newlines as fallback
        paragraphs = [p.strip() for p in text.split("\n") if len(p.strip()) > 10]
    if not paragraphs:
        return "Follow recipe instructions."

    # Skip paragraphs that start with notes/alternatives/add'l
    skip_prefixes = ("alternative", "note:", "tip:", "add'l", "optional:")
    for para in paragraphs:
        if not para.lower().startswith(skip_prefixes):
            first = para
            break
    else:
        first = paragraphs[0]

    # Take first 1-2 sentences
    sentences = re.split(r"(?<=[.!])\s+", first)
    sentences = [s for s in sentences if len(s) > 5]
    if not sentences:
        return "Follow recipe instructions."

    summary = sentences[0]
    if len(sentences) > 1 and len(summary) < 80:
        summary += " " + sentences[1]

    # Truncate if too long
    if len(summary) > 200:
        summary = summary[:197].rsplit(" ", 1)[0] + "..."

    return summary


def estimate_time(recipe: dict) -> tuple[int, int]:
    """Estimate prep and total time in minutes from tags, ingredients, and instructions.

    Returns (prep_min, total_min).
    """
    tags = {t.lower() for t in recipe.get("tags", [])}
    instructions = (recipe.get("instructions") or "").lower()
    n_ingredients = len(recipe.get("ingredients", []))

    # Base prep from ingredient count
    prep = 10 + max(0, (n_ingredients - 5)) * 2  # 10 min + 2 min per extra ingredient

    # Estimate cook time from method signals
    cook = 20  # default

    # Long methods
    if tags & {"stew", "slowcook"} or any(
        w in instructions for w in ["slow cook", "slow-cook", "3-4 hours", "2 hours"]
    ):
        cook = 120
    elif any(w in instructions for w in ["simmer for 1 hour", "simmer for 45", "braise"]):
        cook = 60
    elif tags & {"curry"} or "simmer" in instructions:
        cook = 35
    elif any(w in instructions for w in ["roast", "bake", "oven"]):
        cook = 40
    elif tags & {"soup"}:
        cook = 30
    # Short methods
    elif tags & {"salad"} or "salad" in recipe.get("title", "").lower():
        cook = 5
        prep = max(prep, 10)
    elif "stir-fry" in instructions or "stir fry" in instructions or "wok" in instructions:
        cook = 10
    elif "sandwich" in recipe.get("title", "").lower():
        cook = 10
        prep = min(prep, 15)

    # Cap prep at reasonable range
    prep = max(10, min(prep, 30))
    total = prep + cook

    return prep, total


def build_tags(recipe: dict, total_time: int = 0) -> list[str]:
    """Build a clean tag list for the markdown file."""
    tags = []

    # Add protein tag
    protein_tag = PROTEIN_TAG.get(recipe.get("protein", "unknown"))
    if protein_tag:
        tags.append(protein_tag)

    # Add recipe tags, filtering out noise
    for tag in recipe.get("tags", []):
        tag_lower = tag.lower().strip()
        if tag_lower in SKIP_TAGS:
            continue
        if tag_lower in tags:
            continue
        # Skip country/region tags that overlap with protein
        if tag_lower == recipe.get("protein", ""):
            continue
        tags.append(tag_lower)

    # Add time tag (total time rounded to nearest 5)
    if total_time > 0:
        rounded = 5 * round(total_time / 5)
        tags.append(f"{rounded}min")

    return tags


def clean_instructions(instructions: str) -> str:
    """Clean up raw instructions into readable markdown paragraphs."""
    if not instructions:
        return ""

    text = instructions.replace("\r\n", "\n").replace("\r", "\n")

    # Normalize step headers into bold markdown
    text = re.sub(
        r"^(step\s*\d+)\s*\n",
        lambda m: f"**{m.group(1).title()}**\n",
        text,
        flags=re.MULTILINE | re.IGNORECASE,
    )

    # Clean up excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def recipe_to_markdown(recipe: dict) -> str:
    """Convert a seed recipe dict to markdown string."""
    title = recipe["title"]

    # Ingredients: use normalized_name, title-cased, max 8
    ingredients = recipe.get("ingredients", [])
    ing_names = []
    seen = set()
    for ing in ingredients:
        name = ing.get("normalized_name", "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        ing_names.append(name.title())
        if len(ing_names) >= 8:
            break

    # Prep summary
    prep = extract_prep_summary(recipe.get("instructions", ""))

    # Time estimate
    prep_min, total_min = estimate_time(recipe)

    # Tags (with time-based tags)
    tags = build_tags(recipe, total_min)
    tags_str = " ".join(f"#{t}" for t in tags)

    # Full instructions
    full_instructions = clean_instructions(recipe.get("instructions", ""))

    # Build markdown — Tags stays right after Quick Prep for parser compatibility
    lines = [f"### {title}"]
    lines.append("**Main Ingredients:**  ")
    for name in ing_names:
        lines.append(f"- {name}  ")
    lines.append("")
    lines.append("**Quick Prep:**  ")
    lines.append(prep)
    lines.append("")
    lines.append(f"**Tags:** {tags_str}")
    lines.append("")
    lines.append(f"**Prep Time:** {prep_min} min | **Total Time:** {total_min} min")
    lines.append("")
    if full_instructions:
        lines.append("**Instructions:**  ")
        lines.append(full_instructions)
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    dry_run = "--dry-run" in sys.argv

    if not SEED_FILE.exists():
        print(f"Error: {SEED_FILE} not found. Run scripts/seed.py --fetch first.")
        sys.exit(1)

    with open(SEED_FILE) as f:
        all_recipes = json.load(f)

    # Filter to curated list (case-insensitive matching)
    title_map = {r["title"].lower(): r for r in all_recipes}
    selected = []
    missing = []
    for title in sorted(INCLUDE_TITLES, key=str.lower):
        if title.lower() in title_map:
            selected.append(title_map[title.lower()])
        else:
            missing.append(title)

    if missing:
        print(f"Warning: {len(missing)} titles not found in seed data:")
        for t in missing:
            print(f"  - {t}")
        print()

    print(f"Converting {len(selected)} recipes to markdown...")

    if not dry_run:
        MEALS_DIR.mkdir(exist_ok=True)

    for i, recipe in enumerate(selected):
        num = START_NUMBER + i
        filename = f"{num:02d}_{clean_title_for_filename(recipe['title'])}.md"
        md_content = recipe_to_markdown(recipe)

        if dry_run:
            print(f"\n--- {filename} ---")
            print(md_content)
        else:
            filepath = MEALS_DIR / filename
            filepath.write_text(md_content)

    if not dry_run:
        print(f"Done! Wrote {len(selected)} files to {MEALS_DIR}/")
        print(f"Files numbered {START_NUMBER:02d} to {START_NUMBER + len(selected) - 1:02d}")
    else:
        print(f"\n[DRY RUN] Would write {len(selected)} files")


if __name__ == "__main__":
    main()
