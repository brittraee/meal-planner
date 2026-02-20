"""Meal Planner — Streamlit multi-page application with first-run onboarding."""

import streamlit as st

from src.database import (
    add_pantry_item,
    get_connection,
    get_pantry_items,
    get_user_settings,
    has_completed_onboarding,
    init_db,
    save_user_settings,
)
from src.ingredients import get_ingredients_by_section, get_section, normalize

# ---------------------------------------------------------------------------
# App config & DB init
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Meal Planner",
    page_icon="\U0001f374",
    layout="wide",
)

conn = get_connection()
init_db(conn)


# ---------------------------------------------------------------------------
# Onboarding flow (first-run only)
# ---------------------------------------------------------------------------
def _onboarding():
    """Three-step onboarding wizard."""
    if "onboard_step" not in st.session_state:
        st.session_state.onboard_step = 1

    step = st.session_state.onboard_step

    # Step indicator
    cols = st.columns(3)
    for i, col in enumerate(cols, start=1):
        label = {1: "Welcome", 2: "Pantry", 3: "Done"}[i]
        if i == step:
            col.markdown(f"**:green[{i}. {label}]**")
        elif i < step:
            col.markdown(f"~~{i}. {label}~~")
        else:
            col.markdown(f"{i}. {label}")

    st.divider()

    if step == 1:
        _onboard_welcome()
    elif step == 2:
        _onboard_pantry()
    elif step == 3:
        _onboard_done()


def _onboard_welcome():
    st.header("Meal Planner")
    st.caption("Plan smarter. Shop once. Eat well all week.")

    with st.form("onboard_welcome"):
        name = st.text_input("What should we call you?", placeholder="Brittney")
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
        submitted = st.form_submit_button("Continue", use_container_width=True)

    if submitted:
        if not name.strip():
            st.error("Please enter a name.")
            return
        save_user_settings(conn, name.strip(), servings, meals_per_week)
        st.session_state.onboard_step = 2
        st.rerun()


def _onboard_pantry():
    settings = get_user_settings(conn)
    st.header(f"Hey {settings['name']} \u2014 what's in your kitchen?")
    st.caption("Select ingredients you already have. We'll skip them on grocery lists.")

    sections = get_ingredients_by_section()
    tabs = st.tabs(list(sections.keys()))
    selected_all: list[tuple[str, str]] = []  # (display_name, category)

    for tab, (section, items) in zip(tabs, sections.items()):
        with tab:
            chosen = st.multiselect(
                f"Select {section.lower()} items",
                options=items,
                key=f"onboard_pantry_{section}",
                label_visibility="collapsed",
            )
            for item in chosen:
                selected_all.append((item, get_section(item)))

    st.divider()
    custom = st.text_input(
        "Don't see something? Add it (comma-separated):",
        placeholder="e.g. Tahini, Gochujang, Miso paste",
    )
    custom_items = [c.strip() for c in custom.split(",") if c.strip()] if custom else []

    total_count = len(selected_all) + len(custom_items)
    if total_count:
        st.caption(f"**{total_count}** ingredients selected")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back", use_container_width=True):
            st.session_state.onboard_step = 1
            st.rerun()
    with col2:
        if st.button("Continue", use_container_width=True, type="primary"):
            for display_name, category in selected_all:
                normalized = normalize(display_name)
                add_pantry_item(conn, display_name, normalized, category)
            for item in custom_items:
                normalized = normalize(item)
                add_pantry_item(conn, item, normalized, get_section(item))
            st.session_state.onboard_step = 3
            st.rerun()


def _onboard_done():
    settings = get_user_settings(conn)
    pantry = get_pantry_items(conn)

    st.header(f"You're all set, {settings['name']}!")
    st.caption("Here's a quick summary of your setup.")

    col1, col2, col3 = st.columns(3)
    col1.metric("Servings / meal", settings["servings"])
    col2.metric("Dinners / week", settings["meals_per_week"])
    col3.metric("Pantry items", len(pantry))

    st.divider()
    if st.button("Start Planning", use_container_width=True, type="primary"):
        del st.session_state.onboard_step
        st.rerun()


# ---------------------------------------------------------------------------
# Main app (post-onboarding)
# ---------------------------------------------------------------------------
def _main_app():
    settings = get_user_settings(conn)

    pg = st.navigation(
        {
            "Plan": [
                st.Page("pages/1_recipes.py", title="Recipes", icon="\U0001f4d5", default=True),
                st.Page("pages/2_planner.py", title="Meal Planner", icon="\U0001f4c5"),
                st.Page("pages/3_shopping.py", title="Shopping List", icon="\U0001f6d2"),
            ],
            "Manage": [
                st.Page("pages/4_pantry.py", title="Pantry", icon="\U0001f3ea"),
                st.Page("pages/5_history.py", title="History", icon="\U0001f4ca"),
                st.Page("pages/6_add_recipe.py", title="Add Recipe", icon="\u2795"),
            ],
        }
    )

    if settings:
        st.sidebar.caption(f"Hey {settings['name']}!")

    pg.run()


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
if has_completed_onboarding(conn):
    _main_app()
else:
    _onboarding()
