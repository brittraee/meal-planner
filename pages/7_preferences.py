"""Preferences — settings, pantry management, and reset controls."""

import streamlit as st

from src.database import (
    add_pantry_item,
    clear_user_data,
    delete_pantry_item,
    get_connection,
    get_pantry_items,
    get_user_settings,
    init_db,
    save_user_settings,
)
from src.ingredients import get_ingredients_by_section, get_section, normalize

conn = get_connection()
init_db(conn)

st.title("Preferences")
st.markdown("Adjust your defaults and manage your pantry.")

settings = get_user_settings(conn)
current_servings = settings["servings"] if settings else 4
current_meals = settings["meals_per_week"] if settings else 5

# --- Preferences (no form — save at bottom) ---
with st.container(border=True):
    _serv_col, _meal_col = st.columns(2)
    with _serv_col:
        servings = st.number_input(
            "Default servings per meal",
            min_value=1,
            max_value=10,
            value=current_servings,
            help="Includes adults + kids. You can adjust per-meal later.",
        )
    with _meal_col:
        meals_per_week = st.number_input(
            "Dinners to plan per week",
            min_value=1,
            max_value=7,
            value=current_meals,
            help="Most households do 4-6, leaving room for leftovers or takeout.",
        )

prefs_changed = servings != current_servings or meals_per_week != current_meals

# --- Pantry manager ---
st.divider()
st.subheader("Pantry")
st.caption("Items you keep on hand — these get skipped on shopping lists.")

items = get_pantry_items(conn)
current_names = {i["normalized_name"] for i in items}

if items:
    st.markdown(f"**{len(items)} items**")

    by_cat: dict[str, list[dict]] = {}
    for item in items:
        by_cat.setdefault(item["category"].title(), []).append(item)

    for category in sorted(by_cat):
        cat_items = by_cat[category]
        item_names = [i["name"] for i in cat_items]
        # Key includes count so adding/removing items resets selection
        selected = st.pills(
            category,
            options=item_names,
            default=item_names,
            selection_mode="multi",
            key=f"pantry_{category}_{len(cat_items)}",
        )
        if selected is not None:
            removed = set(item_names) - set(selected)
            if removed:
                for item in cat_items:
                    if item["name"] in removed:
                        delete_pantry_item(conn, item["id"])
                st.rerun()
else:
    st.info(
        "Your pantry is empty. Add items you keep on hand — "
        "they'll be skipped on shopping lists."
    )

# Add from common ingredients
st.markdown("**Add Items**")
sections = get_ingredients_by_section()
tabs = st.tabs(list(sections.keys()))

for tab, (section, section_items) in zip(
    tabs, sections.items(), strict=False
):
    with tab:
        available = [i for i in section_items if normalize(i) not in current_names]
        if available:
            chosen = st.pills(
                f"Select {section.lower()} items",
                options=available,
                selection_mode="multi",
                key=f"pantry_add_{section}",
                label_visibility="collapsed",
            )
            if chosen:
                for item in chosen:
                    add_pantry_item(conn, item, normalize(item), get_section(item))
                st.rerun()
        else:
            st.caption("All items from this section are in your pantry.")

# Custom item
with st.form("add_custom_item"):
    custom_name = st.text_input(
        "Add something else",
        placeholder="e.g. Tahini, Gochujang, Miso paste",
    )
    submitted = st.form_submit_button("Add")

if submitted and custom_name.strip():
    add_pantry_item(
        conn,
        custom_name.strip(),
        normalize(custom_name.strip()),
        get_section(custom_name.strip()),
    )
    st.rerun()

# --- Next steps ---
st.divider()

if prefs_changed:
    st.caption("You have unsaved preference changes.")

_browse_col, _plan_col = st.columns(2)
with _browse_col:
    if st.button(
        "Browse Recipes",
        icon=":material/menu_book:",
        use_container_width=True,
    ):
        if prefs_changed:
            save_user_settings(conn, servings, meals_per_week)
        st.switch_page("pages/1_recipes.py")
with _plan_col:
    if st.button(
        "Generate Meal Plan",
        icon=":material/restaurant:",
        type="primary",
        use_container_width=True,
    ):
        if prefs_changed:
            save_user_settings(conn, servings, meals_per_week)
        st.switch_page("pages/2_planner.py")

# --- Reset section ---
st.divider()
st.markdown("### Reset")

reset_col, clear_col = st.columns(2)

with reset_col:
    if st.button(
        "Reset Preferences",
        icon=":material/restart_alt:",
        help="Reset servings and meals per week to defaults",
    ):
        save_user_settings(conn, 4, 5)
        st.toast("Preferences reset to defaults.")
        st.rerun()

with clear_col:
    if st.button(
        "Clear All Data",
        type="primary",
        icon=":material/delete_forever:",
        help="Remove settings, pantry, and meal plans. Keeps your recipe library.",
    ):
        st.session_state.confirm_clear = True

if st.session_state.get("confirm_clear"):

    @st.dialog("Clear all data?")
    def _confirm_clear():
        st.warning(
            "This removes your settings, pantry items, and meal plans. "
            "Your recipe library stays intact."
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Cancel", use_container_width=True):
                st.session_state.confirm_clear = False
                st.rerun()
        with col2:
            if st.button(
                "Clear Everything",
                type="primary",
                use_container_width=True,
            ):
                clear_user_data(conn)
                st.session_state.confirm_clear = False
                st.switch_page("pages/0_setup.py")

    _confirm_clear()
