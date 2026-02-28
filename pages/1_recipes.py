"""Recipe Library — browsable recipe collection grouped by protein."""

import streamlit as st

from src.database import (
    get_connection,
    get_recipe_details,
    get_unique_proteins,
    get_unique_tags,
    init_db,
    search_recipes,
)
from src.units import format_qty

# --- Custom CSS ---
st.markdown(
    """
    <style>
    /* ---- Recipe card styling ---- */

    /* Center clickable recipe titles */
    [data-testid="stBaseButton-tertiary"] button {
        text-align: center;
        justify-content: center;
        font-size: 1rem;
        font-weight: 500;
    }

    /* Card container: click overlay anchor + spacing */
    [data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stBaseButton-tertiary"]) {
        position: relative;
        cursor: pointer;
        padding: 0.5rem;
        border-radius: 8px;
        transition: background-color 0.15s ease, border-color 0.15s ease;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stBaseButton-tertiary"]):hover {
        background-color: rgba(128, 128, 128, 0.06);
        border-color: rgba(128, 128, 128, 0.25);
    }

    /* Pinned card: warm terracotta tint */
    [data-testid="stVerticalBlockBorderWrapper"]:has(
        button[data-testid="stBaseButton-primary"]
    ) {
        background-color: rgba(194, 105, 79, 0.08);
        border-color: rgba(194, 105, 79, 0.35);
    }

    /* Pinned pin button: compact, above click overlay, red icon */
    [data-testid="stBaseButton-primary"] {
        position: relative;
        z-index: 2;
    }
    button[data-testid="stBaseButton-primary"] {
        padding: 0.15rem 0.4rem;
        min-height: 0;
        background: transparent !important;
        border: none !important;
        color: #D4553B !important;
    }

    /* Stretch title button click area to fill card */
    [data-testid="stBaseButton-tertiary"] button::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 1;
    }

    /* Arrow button: above click overlay, compact */
    [data-testid="stBaseButton-secondary"] {
        position: relative;
        z-index: 2;
    }
    button[data-testid="stBaseButton-secondary"] {
        padding: 0.15rem 0.4rem;
        min-height: 0;
    }

    /* ---- Tag badges ---- */
    .recipe-tags span {
        display: inline-block;
        background: rgba(128, 128, 128, 0.1);
        border-radius: 12px;
        padding: 2px 10px;
        font-size: 0.75rem;
        margin: 1px 2px;
    }

    /* ---- Section expanders: breathing room ---- */
    [data-testid="stExpander"] {
        margin-bottom: 0.5rem;
    }

    /* ---- Section expander headers: bigger click target, visible arrow ---- */
    [data-testid="stExpander"] summary {
        padding: 0.65rem 0.75rem;
        border-radius: 6px;
        transition: background-color 0.15s ease;
        cursor: pointer;
    }
    [data-testid="stExpander"] summary:hover {
        background-color: rgba(128, 128, 128, 0.1);
    }
    [data-testid="stExpander"] summary p {
        font-size: 1rem;
        font-weight: 600;
    }
    [data-testid="stExpander"] summary svg {
        width: 1.25em;
        height: 1.25em;
        opacity: 0.9;
    }

    /* ---- Mobile-friendly adjustments ---- */
    @media (max-width: 768px) {
        /* Smaller page title */
        [data-testid="stTitle"] { font-size: 1.4rem; }

        /* Tighter section expander spacing */
        [data-testid="stExpander"] { margin-bottom: 0.25rem; }

        /* Compact filter pills */
        button[data-testid="stPillButton"] {
            font-size: 0.78rem;
            padding: 0.15rem 0.5rem;
        }

        /* Reduce top page padding */
        .stMainBlockContainer { padding-top: 1rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Recipe Library")
st.caption(
    "Filter by ingredient, tags, or keyword. "
    "Click a card for details, pin favorites for your meal plan."
)

conn = get_connection()
init_db(conn)

# --- Pinned recipes (session state) ---
if "pinned_recipes" not in st.session_state:
    st.session_state.pinned_recipes = {}

pinned = st.session_state.pinned_recipes

# Check if recipes exist
all_recipes = search_recipes(conn)
if not all_recipes:
    st.warning("No recipes found. Add recipes via the Add Recipe page.")
    st.stop()

# --- Filter bar ---
proteins = get_unique_proteins(conn)
# Exclude time tags and tags that duplicate ingredient/protein pills
_SKIP_TAGS = {"pasta", "steak", "side", "staple", "taco", "tacos", "lowcarb"}
available_tags = [
    t for t in get_unique_tags(conn)
    if not t.rstrip("min").isdigit() and t not in _SKIP_TAGS
]
time_options = ["Any", "15 min", "30 min", "45 min", "60 min", "90 min", "120 min"]
time_values = {
    "Any": None, "15 min": 15, "30 min": 30, "45 min": 45,
    "60 min": 60, "90 min": 90, "120 min": 120,
}

_TAG_DISPLAY: dict[str, str] = {
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

with st.expander("Filters", expanded=False, icon=":material/filter_list:"):
    time_col, search_col, _ = st.columns([1, 2, 2])
    with time_col:
        selected_time = st.selectbox("Max Time", time_options)
    with search_col:
        search_text = st.text_input("Search", placeholder="e.g. pasta, taco...")

    # Ingredient pills
    _staples = ["rice", "pasta", "potato", "broccoli", "spinach", "mushroom",
                 "cheese", "tortilla", "noodles"]
    _ing_options = proteins + [s for s in _staples if s not in proteins]
    st.markdown("**Ingredients** — show recipes with any of these")
    selected_ingredients = st.pills(
        "Filter by ingredient",
        options=_ing_options,
        selection_mode="multi",
        format_func=str.title,
        key="recipe_ingredient_pills",
        label_visibility="collapsed",
    ) or []

    # Sub-category refinement for selected proteins
    _PROTEIN_SUBS: dict[str, list[str]] = {
        "beef": ["ground beef", "steak", "roast", "brisket"],
        "chicken": ["breast", "thigh", "drumstick", "whole chicken"],
        "pork": ["pork loin", "pork tenderloin", "pork shoulder"],
        "shrimp": ["large shrimp", "jumbo shrimp"],
        "turkey": ["ground turkey"],
    }
    _sub_picks: list[str] = []
    for _ing in selected_ingredients:
        if _ing in _PROTEIN_SUBS:
            _subs = st.pills(
                f"{_ing.title()} type",
                options=_PROTEIN_SUBS[_ing],
                selection_mode="multi",
                format_func=str.title,
                key=f"recipe_sub_{_ing}",
                label_visibility="collapsed",
            ) or []
            _sub_picks.extend(_subs)

    # Build final ingredient list: use sub-picks where available
    _final_ingredients: list[str] = []
    for _ing in selected_ingredients:
        if _ing in _PROTEIN_SUBS and _sub_picks:
            _my_subs = [s for s in _sub_picks if s in _PROTEIN_SUBS[_ing]]
            if _my_subs:
                _final_ingredients.extend(_my_subs)
            else:
                _final_ingredients.append(_ing)
        else:
            _final_ingredients.append(_ing)

    # Tag pills
    st.markdown("**Tags**")
    selected_tags = st.pills(
        "Filter by tag",
        options=available_tags,
        selection_mode="multi",
        format_func=lambda t: _TAG_DISPLAY.get(t, t.title()),
        key="recipe_tag_pills",
        label_visibility="collapsed",
    ) or []

max_time = time_values[selected_time]

# --- Query recipes ---
results = search_recipes(
    conn,
    query=search_text or None,
    tags=selected_tags or None,
    max_time=max_time,
    ingredients=_final_ingredients or None,
)

# --- Sidebar: pinned recipes + planner link ---
with st.sidebar:
    st.markdown("### Pinned Recipes")
    if pinned:
        for rid, title in list(pinned.items()):
            pin_col, unpin_col = st.columns([5, 1])
            with pin_col:
                st.markdown(f"**{title}**")
            with unpin_col:
                if st.button(
                    "",
                    key=f"sidebar_unpin_{rid}",
                    icon=":material/close:",
                    type="tertiary",
                ):
                    del st.session_state.pinned_recipes[rid]
                    st.rerun()
        st.divider()
        st.page_link(
            "pages/2_planner.py",
            label=f"Generate Plan ({len(pinned)} pinned)",
            icon=":material/calendar_month:",
        )
        if st.button("Clear all pins", type="tertiary", icon=":material/delete:"):
            st.session_state.pinned_recipes = {}
            st.rerun()
    else:
        st.caption("Pin recipes to build your meal plan.")

# --- Group recipes by section ---
BREAKFAST_TAGS = {"breakfast", "brinner"}

SECTION_ICONS = {
    "My Recipes": "\U0001f516",
    "Breakfast": "\U0001f373",
    "Poultry": "\U0001f357",
    "Beef": "\U0001f969",
    "Pork": "\U0001f953",
    "Seafood": "\U0001f41f",
    "Vegetarian": "\U0001f96c",
    "Vegan": "\U0001f331",
    "Side": "\U0001f957",
}

SECTION_ORDER = [
    "My Recipes", "Breakfast", "Poultry", "Beef", "Pork",
    "Seafood", "Vegetarian", "Vegan", "Side",
]

# Accent colors per section (warm for meat, cool for seafood, green for plant)
SECTION_COLORS = {
    "My Recipes": "#C2694F",
    "Breakfast": "#D4956A",
    "Poultry": "#C2694F",
    "Beef": "#A0522D",
    "Pork": "#B87850",
    "Seafood": "#5E8E8B",
    "Vegetarian": "#7D9B76",
    "Vegan": "#6B8E5A",
    "Side": "#8B8B3A",
}


_PROTEIN_TO_SECTION = {
    "chicken": "Poultry",
    "turkey": "Poultry",
    "fish": "Seafood",
    "shrimp": "Seafood",
    "seafood": "Seafood",
}


def _get_section(recipe: dict) -> str:
    """Determine which section a recipe belongs to."""
    tags = set(recipe.get("tags", []))
    if tags & BREAKFAST_TAGS:
        return "Breakfast"
    protein = (recipe.get("protein") or "other").lower()
    return _PROTEIN_TO_SECTION.get(protein, protein.title())


sections: dict[str, list[dict]] = {}
for recipe in results:
    if recipe.get("source_type") in ("url", "manual"):
        sections.setdefault("My Recipes", []).append(recipe)
    section = _get_section(recipe)
    sections.setdefault(section, []).append(recipe)

# Known order first, then any remaining alphabetically
ordered_sections = [s for s in SECTION_ORDER if s in sections]
ordered_sections.extend(sorted(s for s in sections if s not in SECTION_ORDER))

# --- Active filters + recipe count ---
active = []
if selected_ingredients:
    active.append(f"Ingredients: {', '.join(i.title() for i in selected_ingredients)}")
if selected_tags:
    active.append(f"Tags: {', '.join(_TAG_DISPLAY.get(t, t.title()) for t in selected_tags)}")
if selected_time != "Any":
    active.append(f"Max: {selected_time}")
if search_text:
    active.append(f'"{search_text}"')
if active:
    st.caption("Filtering by: " + " \u00b7 ".join(active))
st.caption(f"{len(results)} recipes")

# --- Render sections ---
COLS_PER_ROW = 3

if results:
    for section_name in ordered_sections:
        section_recipes = sections[section_name]
        icon = SECTION_ICONS.get(section_name, "\U0001f372")
        color = SECTION_COLORS.get(section_name, "#888")
        st.markdown(
            f'<div style="height:3px;background:{color};'
            f'border-radius:2px;margin-bottom:-0.6rem"></div>',
            unsafe_allow_html=True,
        )
        with st.expander(
            f"{icon} {section_name} ({len(section_recipes)})", expanded=False
        ):
            for row_start in range(0, len(section_recipes), COLS_PER_ROW):
                row_recipes = section_recipes[row_start : row_start + COLS_PER_ROW]
                cols = st.columns(COLS_PER_ROW)

                for col, recipe in zip(cols, row_recipes, strict=False):
                    is_pinned = recipe["id"] in pinned
                    recipe_id = recipe["id"]

                    with col, st.container(border=True):
                        # Top row: arrow + title + pin icon
                        is_viewing = st.session_state.get("viewing_recipe") == recipe_id
                        arrow = "\u25BC" if is_viewing else "\u25B6"
                        arrow_col, title_col, pin_col = st.columns(
                            [0.5, 5, 0.5]
                        )
                        with arrow_col:
                            arrow_icon = (
                                ":material/expand_more:"
                                if is_viewing
                                else ":material/chevron_right:"
                            )
                            if st.button(
                                "",
                                key=f"arrow_{recipe_id}",
                                icon=arrow_icon,
                                type="secondary",
                            ):
                                if is_viewing:
                                    del st.session_state["viewing_recipe"]
                                else:
                                    st.session_state.viewing_recipe = recipe_id
                                st.rerun()
                        with title_col:
                            if st.button(
                                recipe["title"],
                                key=f"view_{recipe_id}",
                                use_container_width=True,
                                type="tertiary",
                            ):
                                if is_viewing:
                                    del st.session_state["viewing_recipe"]
                                else:
                                    st.session_state.viewing_recipe = recipe_id
                                st.rerun()
                        with pin_col:
                            btn_type = "primary" if is_pinned else "tertiary"
                            pin_icon = ":material/push_pin:" if is_pinned else ":material/keep:"
                            if st.button(
                                "",
                                key=f"pin_{recipe_id}",
                                type=btn_type,
                                icon=pin_icon,
                                help="Unpin" if is_pinned else "Pin to meal plan",
                            ):
                                if is_pinned:
                                    del st.session_state.pinned_recipes[recipe_id]
                                else:
                                    st.session_state.pinned_recipes[recipe_id] = recipe["title"]
                                st.rerun()

                # --- Inline detail panel (below the row containing the clicked card) ---
                for recipe in row_recipes:
                    if st.session_state.get("viewing_recipe") == recipe["id"]:
                        details = get_recipe_details(conn, recipe["id"])
                        if details:
                            with st.container(border=True):
                                info_col, ing_col = st.columns(2)
                                with info_col:
                                    st.markdown(f"**Protein:** {details['protein']}")
                                    st.markdown(f"**Servings:** {details.get('servings') or 4}")
                                    if details.get("tags"):
                                        tag_html = " ".join(
                                            f"<span>{t}</span>"
                                            for t in details["tags"]
                                        )
                                        st.markdown(
                                            f'<div class="recipe-tags">{tag_html}</div>',
                                            unsafe_allow_html=True,
                                        )
                                with ing_col:
                                    lines = []
                                    for ing in details["ingredients"]:
                                        optional = " *(optional)*" if ing["is_optional"] else ""
                                        if ing.get("qty"):
                                            qs = format_qty(ing["qty"])
                                            unit = f" {ing['unit']}" if ing.get("unit") else ""
                                            lines.append(
                                                f"- {qs}{unit} {ing['normalized_name']}{optional}"
                                            )
                                        else:
                                            lines.append(f"- {ing['normalized_name']}{optional}")
                                    st.markdown("**Ingredients:**\n" + "\n".join(lines))

else:
    st.info("No recipes match the current filters.")

# --- Bottom navigation to Meal Planner ---
st.divider()
st.page_link(
    "pages/2_planner.py",
    label=f"Continue to Meal Planner ({len(pinned)} pinned)" if pinned else "Continue to Meal Planner",
    icon=":material/arrow_forward:",
)
