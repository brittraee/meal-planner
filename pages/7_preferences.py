"""Preferences — adjust servings, meals per week, and manage pantry."""

import streamlit as st

from src.database import (
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
