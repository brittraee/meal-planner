"""Get Started — first-run setup page."""

import streamlit as st

from src.database import (
    add_pantry_item,
    get_connection,
    get_pantry_items,
    init_db,
    save_user_settings,
)
from src.ingredients import DEFAULT_PANTRY, get_ingredients_by_section, get_section, normalize

conn = get_connection()
init_db(conn)

# Pre-populate common staples on first visit
if not get_pantry_items(conn):
    for item in DEFAULT_PANTRY:
        add_pantry_item(conn, item, normalize(item), get_section(item))

st.title("Get Started")
st.caption("Set your defaults, then head to the Recipe Library.")

# --- Section 1: Meal defaults ---
st.subheader("Meal Defaults")

servings = st.slider(
    "Default servings per meal",
    min_value=1,
    max_value=10,
    value=4,
    help="Includes adults + kids. You can adjust per-meal later.",
)
meals_per_week = st.select_slider(
    "Dinners to plan per week",
    options=list(range(1, 8)),
    value=5,
    help="Most households do 4-6, leaving room for leftovers or takeout.",
)

# --- Section 2: Quick pantry setup ---
st.divider()
st.subheader("Pantry Staples")
st.caption(
    "Add what you keep on hand — these get skipped on shopping lists "
    "so you only buy what you need."
)

items = get_pantry_items(conn)
current_names = {i["normalized_name"] for i in items}

sections = get_ingredients_by_section()
tabs = st.tabs(list(sections.keys()))

for tab, (section, section_items) in zip(tabs, sections.items(), strict=False):
    with tab:
        available = [i for i in section_items if normalize(i) not in current_names]
        if available:
            chosen = st.pills(
                f"Select {section.lower()} items",
                options=available,
                selection_mode="multi",
                key=f"setup_pantry_{section}",
                label_visibility="collapsed",
            )
            if chosen:
                for item in chosen:
                    add_pantry_item(conn, item, normalize(item), get_section(item))
                st.rerun()
        else:
            st.caption("All items from this section are in your pantry.")

pantry_count = len(get_pantry_items(conn))
if pantry_count:
    st.success(f"{pantry_count} pantry items added.")

# --- Save & Start ---
st.divider()
if st.button("Save & Start", type="primary", icon=":material/rocket_launch:"):
    save_user_settings(conn, servings, meals_per_week)
    st.switch_page("pages/1_recipes.py")
