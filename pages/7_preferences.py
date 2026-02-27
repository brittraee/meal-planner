"""Preferences — adjust servings, meals per week, and manage pantry."""

import streamlit as st

from src.database import (
    clear_user_data,
    get_connection,
    get_pantry_items,
    get_user_settings,
    init_db,
    save_user_settings,
)

conn = get_connection()
init_db(conn)

st.title("Meal Preferences")
st.caption("Adjust your meal planning defaults.")

settings = get_user_settings(conn)
current_servings = settings["servings"] if settings else 4
current_meals = settings["meals_per_week"] if settings else 5

servings = st.slider(
    "Default servings per meal",
    min_value=1,
    max_value=10,
    value=current_servings,
    help="Includes adults + kids. You can adjust per-meal later.",
)
meals_per_week = st.select_slider(
    "Dinners to plan per week",
    options=list(range(1, 8)),
    value=current_meals,
    help="Most households do 4-6, leaving room for leftovers or takeout.",
)

if servings != current_servings or meals_per_week != current_meals:
    save_user_settings(conn, servings, meals_per_week)
    st.toast("Preferences saved.")

# --- Pantry summary ---
st.divider()
pantry = get_pantry_items(conn)
st.markdown(f"**{len(pantry)}** pantry items")
st.caption("Pantry items are skipped on shopping lists.")
st.page_link(
    "pages/4_pantry.py",
    label="Manage Pantry",
    icon=":material/grocery:",
)

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
                st.toast("All user data cleared.")
                st.rerun()

    _confirm_clear()
