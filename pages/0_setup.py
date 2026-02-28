"""Get Started — first-run setup page."""

import streamlit as st

from src.database import (
    add_pantry_item,
    clear_pantry,
    get_connection,
    get_pantry_items,
    init_db,
    save_user_settings,
)
from src.ingredients import DEFAULT_PANTRY, get_ingredients_by_section, get_section, normalize

conn = get_connection()
init_db(conn)

# ---------------------------------------------------------------------------
# Welcome screen (shown before setup form)
# ---------------------------------------------------------------------------
if not st.session_state.get("show_setup_form"):
    st.title("Welcome to Meal Planner")
    st.markdown(
        "Plan your week, shop smarter, waste less. "
        "Here's what you can do:"
    )

    cols = st.columns(3)
    with cols[0]:
        st.markdown("#### Plan Meals")
        st.caption(
            "Generate a balanced week of dinners with protein variety, "
            "tag priorities, and pinned favorites."
        )
    with cols[1]:
        st.markdown("#### Smart Shopping")
        st.caption(
            "Auto-generated lists grouped by store section. "
            "Pantry staples are filtered out so you only buy what you need."
        )
    with cols[2]:
        st.markdown("#### Track Your Pantry")
        st.caption(
            "Mark what you keep on hand. Shopping lists "
            "adjust automatically — no duplicates."
        )

    st.markdown("")
    if st.button("Let's set up", type="primary", icon=":material/arrow_forward:"):
        st.session_state.show_setup_form = True
        st.rerun()
    st.stop()

# ---------------------------------------------------------------------------
# Setup form
# ---------------------------------------------------------------------------
st.title("Get Started")
st.caption("Set your defaults, then head to the Recipe Library.")

# --- Section 1: Meal defaults ---
st.subheader("Meal Defaults")

_serv_col, _meal_col = st.columns(2)
with _serv_col:
    servings = st.number_input(
        "Default servings per meal",
        min_value=1,
        max_value=10,
        value=4,
        help="Includes adults + kids. You can adjust per-meal later.",
    )
with _meal_col:
    meals_per_week = st.number_input(
        "Dinners to plan per week",
        min_value=1,
        max_value=7,
        value=5,
        help="Most households do 4-6, leaving room for leftovers or takeout.",
    )

# --- Section 2: Quick pantry setup ---
st.divider()
st.subheader("Pantry Staples")
st.caption(
    "Select what you keep on hand — these get skipped on shopping lists. "
    "Common staples are pre-selected."
)

# Initialize pill defaults: use existing pantry if available, else DEFAULT_PANTRY
sections = get_ingredients_by_section()
if "setup_pantry_initialized" not in st.session_state:
    existing = get_pantry_items(conn)
    if existing:
        preselected = {i["normalized_name"] for i in existing}
    else:
        preselected = {normalize(name) for name in DEFAULT_PANTRY}
    for section, section_items in sections.items():
        key = f"setup_pantry_{section}"
        st.session_state[key] = [
            i for i in section_items if normalize(i) in preselected
        ]
    st.session_state.setup_pantry_initialized = True

# Show all items as pills with defaults pre-selected
# Order: Pantry first (most common staples), then the rest
_SECTION_ORDER = ["Pantry", "Produce", "Dairy", "Protein", "Frozen"]
ordered = [(s, sections[s]) for s in _SECTION_ORDER if s in sections]
ordered.extend((s, sections[s]) for s in sections if s not in _SECTION_ORDER)

tabs = st.tabs([s for s, _ in ordered])
total_selected = 0

for tab, (section, section_items) in zip(tabs, ordered, strict=False):
    with tab:
        chosen = st.pills(
            f"Select {section.lower()} items",
            options=section_items,
            selection_mode="multi",
            key=f"setup_pantry_{section}",
            label_visibility="collapsed",
        ) or []
        total_selected += len(chosen)

if total_selected:
    st.success(f"{total_selected} pantry items selected.")

# --- Save & Start ---
st.divider()
if st.button("Save & Start", type="primary", icon=":material/rocket_launch:"):
    # Sync pill selections to DB
    clear_pantry(conn)
    for section, section_items in sections.items():
        key = f"setup_pantry_{section}"
        selected = st.session_state.get(key, [])
        for name in selected:
            add_pantry_item(conn, name, normalize(name), get_section(name))
    save_user_settings(conn, servings, meals_per_week)
    st.session_state.pop("show_setup_form", None)
    st.session_state.pop("setup_pantry_initialized", None)
    st.switch_page("pages/1_recipes.py")
