"""Meal Planner — Streamlit multi-page application."""

import streamlit as st

from src.database import (
    get_connection,
    get_pantry_items,
    get_user_settings,
    has_completed_onboarding,
    init_db,
    save_user_settings,
)

# ---------------------------------------------------------------------------
# App config & DB init
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Meal Planner",
    page_icon="\U0001f374",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """<style>
    a.stHeaderLink { display: none !important; }

    /* Colored sidebar nav icons */
    [data-testid="stSidebarNavItems"] li:nth-child(1) span[data-testid="stIconMaterial"] {
        color: #cb9e21;  /* Recipe Library — gold */
    }
    [data-testid="stSidebarNavItems"] li:nth-child(2) span[data-testid="stIconMaterial"] {
        color: #5BA0B5;  /* Meal Planner — teal */
    }
    [data-testid="stSidebarNavItems"] li:nth-child(3) span[data-testid="stIconMaterial"] {
        color: #6ABF69;  /* Shopping List — green */
    }
    [data-testid="stSidebarNavItems"] li:nth-child(4) span[data-testid="stIconMaterial"] {
        color: #E8985A;  /* Pantry — warm orange */
    }
    [data-testid="stSidebarNavItems"] li:nth-child(5) span[data-testid="stIconMaterial"] {
        color: #A0CC93;  /* Add Recipe — sage */
    }
    [data-testid="stSidebarNavItems"] li:nth-child(6) span[data-testid="stIconMaterial"] {
        color: #B0B0B0;  /* Preferences — neutral gray */
    }
    </style>""",
    unsafe_allow_html=True,
)

conn = get_connection()
init_db(conn)

# Auto-create default settings on first run
if not has_completed_onboarding(conn):
    save_user_settings(conn, servings=4, meals_per_week=5)

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
settings = get_user_settings(conn)

pg = st.navigation(
    {
        "Plan": [
            st.Page(
                "pages/1_recipes.py", title="Recipe Library",
                icon=":material/menu_book:", default=True,
            ),
            st.Page("pages/2_planner.py", title="Meal Planner", icon=":material/calendar_month:"),
            st.Page("pages/3_shopping.py", title="Shopping List", icon=":material/shopping_cart:"),
        ],
        "Manage": [
            st.Page("pages/4_pantry.py", title="Pantry", icon=":material/kitchen:"),
            st.Page("pages/6_add_recipe.py", title="Add Recipe", icon=":material/add_circle:"),
            st.Page("pages/7_preferences.py", title="Meal Preferences", icon=":material/tune:"),
        ],
    }
)

if settings:
    pantry = get_pantry_items(conn)
    st.sidebar.markdown(
        f"**{settings['servings']}** servings/meal · "
        f"**{settings['meals_per_week']}** dinners/week · "
        f"**{len(pantry)}** pantry items"
    )

pg.run()
