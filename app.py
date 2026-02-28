"""Meal Planner — Streamlit multi-page application."""

import streamlit as st

from src.database import (
    get_connection,
    get_pantry_items,
    get_user_settings,
    has_completed_onboarding,
    init_db,
)

# ---------------------------------------------------------------------------
# App config & DB init
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Meal Planner",
    page_icon="\U0001f374",
    layout="wide",
    initial_sidebar_state="auto",
)

st.markdown(
    """<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    a.stHeaderLink { display: none !important; }

    /* Colored sidebar nav icons */
    [data-testid="stSidebarNavItems"] li:nth-child(1) span[data-testid="stIconMaterial"] {
        color: #C2694F;  /* Recipe Library — terracotta */
    }
    [data-testid="stSidebarNavItems"] li:nth-child(2) span[data-testid="stIconMaterial"] {
        color: #7D9B76;  /* Meal Planner — dusty sage */
    }
    [data-testid="stSidebarNavItems"] li:nth-child(3) span[data-testid="stIconMaterial"] {
        color: #8B8B3A;  /* Shopping List — olive */
    }
    [data-testid="stSidebarNavItems"] li:nth-child(4) span[data-testid="stIconMaterial"] {
        color: #D4956A;  /* Pantry — warm copper */
    }
    [data-testid="stSidebarNavItems"] li:nth-child(5) span[data-testid="stIconMaterial"] {
        color: #7D9B76;  /* Add Recipe — sage */
    }
    [data-testid="stSidebarNavItems"] li:nth-child(6) span[data-testid="stIconMaterial"] {
        color: #9B8F82;  /* Preferences — warm gray */
    }

    </style>""",
    unsafe_allow_html=True,
)

conn = get_connection()
init_db(conn)

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
onboarded = has_completed_onboarding(conn)
settings = get_user_settings(conn)

plan_pages = [
    st.Page(
        "pages/1_recipes.py", title="Recipe Library",
        icon=":material/menu_book:", default=onboarded,
    ),
    st.Page("pages/2_planner.py", title="Meal Planner", icon=":material/calendar_month:"),
    st.Page("pages/3_shopping.py", title="Shopping List", icon=":material/shopping_cart:"),
]
manage_pages = [
    st.Page("pages/4_pantry.py", title="Pantry", icon=":material/kitchen:"),
    st.Page("pages/6_add_recipe.py", title="Add Recipe", icon=":material/add_circle:"),
    st.Page("pages/7_preferences.py", title="Meal Preferences", icon=":material/tune:"),
]

nav: dict[str, list] = {}
if not onboarded:
    nav[""] = [
        st.Page(
            "pages/0_setup.py", title="Get Started",
            icon=":material/rocket_launch:", default=True,
        ),
    ]
    nav["Plan"] = plan_pages
    nav["Manage"] = manage_pages
else:
    nav["Plan"] = plan_pages
    nav["Manage"] = manage_pages + [
        st.Page("pages/0_setup.py", title="Re-run Setup", icon=":material/rocket_launch:"),
    ]

pg = st.navigation(nav)

if settings:
    pantry = get_pantry_items(conn)
    st.sidebar.markdown(
        f"**{settings['servings']}** servings/meal · "
        f"**{settings['meals_per_week']}** dinners/week · "
        f"**{len(pantry)}** pantry items"
    )

pg.run()
