"""Recipe browser — single scrollable page grouped by protein."""

import streamlit as st

from src.database import (
    get_connection,
    get_recipe_details,
    get_unique_proteins,
    get_unique_tags,
    init_db,
    search_recipes,
)

# --- Custom CSS ---
st.markdown(
    """
    <style>
    /* ---- Recipe card styling ---- */

    /* Left-align clickable recipe titles */
    [data-testid="stBaseButton-tertiary"] button {
        text-align: left;
        justify-content: flex-start;
        font-size: 1rem;
        font-weight: 500;
    }

    /* Card container: click overlay anchor + spacing */
    [data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stBaseButton-tertiary"]) {
        position: relative;
        cursor: pointer;
        padding: 0.25rem;
        border-radius: 8px;
        transition: background-color 0.15s ease, border-color 0.15s ease;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stBaseButton-tertiary"]):hover {
        background-color: rgba(128, 128, 128, 0.06);
        border-color: rgba(128, 128, 128, 0.25);
    }

    /* Pinned card: subtle tint + stronger border */
    [data-testid="stVerticalBlockBorderWrapper"]:has(
        button[data-testid="stBaseButton-secondary"]:not([kind="tertiary"])
    ) {
        background-color: rgba(46, 134, 193, 0.06);
        border-color: rgba(46, 134, 193, 0.3);
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

    /* Pin button: above click overlay, compact */
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
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Recipe Browser")
st.caption(
    "Click any recipe to see ingredients and prep details. "
    "Pin recipes to lock them into your meal plan."
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
    st.warning("No recipes found. Run `python scripts/ingest.py` to import your recipe cards.")
    st.stop()

# --- Filter bar ---
proteins = get_unique_proteins(conn)
available_tags = [t for t in get_unique_tags(conn) if not t.rstrip("min").isdigit()]
time_options = ["Any", "15 min", "30 min", "45 min", "60 min", "90 min", "120 min"]
time_values = {
    "Any": None, "15 min": 15, "30 min": 30, "45 min": 45,
    "60 min": 60, "90 min": 90, "120 min": 120,
}

protein_col, time_col, tags_col, spacer, search_col = st.columns([1.5, 1.5, 2.5, 0.5, 2])
with protein_col:
    selected_protein = st.selectbox("Protein", ["All", *proteins])
with time_col:
    selected_time = st.selectbox("Max Time", time_options)
with tags_col:
    selected_tags = st.multiselect("Tags", available_tags)
with search_col:
    search_text = st.text_input("Search", placeholder="e.g. pasta, taco...")

max_time = time_values[selected_time]

# --- Query recipes ---
results = search_recipes(
    conn,
    query=search_text or None,
    tags=selected_tags or None,
    protein=selected_protein if selected_protein != "All" else None,
    max_time=max_time,
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
BREAKFAST_TAGS = {"breakfastfordinner", "brinner", "breakfast"}

SECTION_ICONS = {
    "Breakfast": "\U0001f373",
    "Chicken": "\U0001f357",
    "Beef": "\U0001f969",
    "Pork": "\U0001f953",
    "Turkey": "\U0001f983",
    "Fish": "\U0001f41f",
    "Shrimp": "\U0001f990",
    "Seafood": "\U0001f99e",
    "Vegetarian": "\U0001f96c",
    "Vegan": "\U0001f331",
    "Side": "\U0001f957",
}

SECTION_ORDER = [
    "Breakfast", "Chicken", "Beef", "Pork", "Turkey",
    "Fish", "Shrimp", "Seafood", "Vegetarian", "Vegan", "Side",
]


def _get_section(recipe: dict) -> str:
    """Determine which section a recipe belongs to."""
    tags = set(recipe.get("tags", []))
    if tags & BREAKFAST_TAGS:
        return "Breakfast"
    protein = recipe.get("protein", "Other") or "Other"
    return protein.title()


sections: dict[str, list[dict]] = {}
for recipe in results:
    section = _get_section(recipe)
    sections.setdefault(section, []).append(recipe)

# Known order first, then any remaining alphabetically
ordered_sections = [s for s in SECTION_ORDER if s in sections]
ordered_sections.extend(sorted(s for s in sections if s not in SECTION_ORDER))

# --- Recipe count ---
st.caption(f"{len(results)} recipes")

# --- Render sections ---
COLS_PER_ROW = 4

if results:
    for section_name in ordered_sections:
        section_recipes = sections[section_name]
        icon = SECTION_ICONS.get(section_name, "\U0001f372")
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
                            # Top row: title + pin icon
                            title_col, pin_col = st.columns([5, 1])
                            with title_col:
                                is_viewing = st.session_state.get("viewing_recipe") == recipe_id
                                arrow = "\u25BC" if is_viewing else "\u25B6"
                                if st.button(
                                    f"{arrow} {recipe['title']}",
                                    key=f"view_{recipe_id}",
                                    use_container_width=True,
                                    type="tertiary",
                                ):
                                    if st.session_state.get("viewing_recipe") == recipe_id:
                                        del st.session_state["viewing_recipe"]
                                    else:
                                        st.session_state.viewing_recipe = recipe_id
                                    st.rerun()
                            with pin_col:
                                btn_type = "secondary" if is_pinned else "tertiary"
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

                            if recipe.get("tags"):
                                display_tags = [
                                    t for t in recipe["tags"]
                                    if not t.rstrip("min").isdigit()
                                ]
                                if display_tags:
                                    tag_html = " ".join(
                                        f"<span>{t}</span>" for t in display_tags
                                    )
                                    st.markdown(
                                        f'<div class="recipe-tags">{tag_html}</div>',
                                        unsafe_allow_html=True,
                                    )

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
                                    if details.get("prep_notes"):
                                        st.markdown(f"**Prep:** {details['prep_notes']}")
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
                                            q = ing["qty"]
                                            qs = str(int(q)) if q == int(q) else f"{q:g}"
                                            unit = f" {ing['unit']}" if ing.get("unit") else ""
                                            lines.append(
                                                f"- {qs}{unit} {ing['normalized_name']}{optional}"
                                            )
                                        else:
                                            lines.append(f"- {ing['normalized_name']}{optional}")
                                    st.markdown("**Ingredients:**\n" + "\n".join(lines))

else:
    st.info("No recipes match the current filters.")
