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

st.markdown(
    "<style>a.stHeaderLink { display: none !important; }</style>",
    unsafe_allow_html=True,
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
        name = st.text_input("What should we call you?", placeholder="Name")
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
        st.session_state.onboard_data = {
            "name": name.strip(),
            "servings": servings,
            "meals_per_week": meals_per_week,
        }
        st.session_state.onboard_step = 2
        st.rerun()


def _onboard_pantry():
    data = st.session_state.get("onboard_data", {})
    st.header(f"Hey {data.get('name', '')} \u2014 what's in your kitchen?")
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

    st.divider()
    prioritize_pantry = st.checkbox(
        "Prioritize recipes that use ingredients I already have",
        value=True,
        help="The meal planner will score recipes higher if they match your pantry items.",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back", use_container_width=True):
            st.session_state.onboard_step = 1
            st.rerun()
    with col2:
        if st.button("Continue", use_container_width=True, type="primary"):
            # Store pantry selections in session state — DB write happens in step 3
            st.session_state.onboard_pantry = {
                "selected": selected_all,
                "custom": custom_items,
            }
            st.session_state.onboard_step = 3
            st.rerun()


def _onboard_done():
    data = st.session_state.get("onboard_data", {})
    pantry_data = st.session_state.get("onboard_pantry", {})
    pantry_count = len(pantry_data.get("selected", [])) + len(pantry_data.get("custom", []))

    st.header(f"You're all set, {data.get('name', '')}!")
    st.caption("Here's a quick summary of your setup.")

    col1, col2, col3 = st.columns(3)
    col1.metric("Servings / meal", data.get("servings", 4))
    col2.metric("Dinners / week", data.get("meals_per_week", 5))
    col3.metric("Pantry items", pantry_count)

    st.divider()
    st.subheader("Here's how it works")

    st.markdown(
        "We've included **150+ curated recipes** to get you started — "
        "and you can add your own anytime.\n\n"
        "**Browse Recipes** — Pin favorites or let the planner choose for you.\n\n"
        "**Meal Planner** — Generate a week of dinners in one click.\n\n"
        "**Shopping List** — Grouped by store section, pantry items filtered out.\n\n"
        "**Pantry** — Keep it updated for smarter lists."
    )

    st.divider()
    if st.button("Start Planning", use_container_width=True, type="primary"):
        # Write all onboarding data to DB
        save_user_settings(conn, data["name"], data["servings"], data["meals_per_week"])
        for display_name, category in pantry_data.get("selected", []):
            add_pantry_item(conn, display_name, normalize(display_name), category)
        for item in pantry_data.get("custom", []):
            add_pantry_item(conn, item, normalize(item), get_section(item))
        # Clean up session state
        del st.session_state.onboard_step
        st.session_state.pop("onboard_data", None)
        st.session_state.pop("onboard_pantry", None)
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
                st.Page("pages/6_add_recipe.py", title="Add Recipe", icon="\u2795"),
            ],
        }
    )

    if settings:
        st.sidebar.caption(f"Hey {settings['name']}!")
        pantry = get_pantry_items(conn)
        st.sidebar.markdown(
            f"**{settings['servings']}** servings/meal · "
            f"**{settings['meals_per_week']}** dinners/week · "
            f"**{len(pantry)}** pantry items"
        )
        if st.sidebar.button("Reset preferences", use_container_width=True):
            conn.execute("DELETE FROM user_settings")
            conn.execute("DELETE FROM pantry_items")
            conn.commit()
            st.rerun()

    pg.run()


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
if has_completed_onboarding(conn):
    _main_app()
else:
    _onboarding()
