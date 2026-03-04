"""Get Started — welcome page with smart defaults."""

import streamlit as st

from src.database import (
    add_pantry_item,
    get_connection,
    init_db,
    save_user_settings,
)
from src.ingredients import DEFAULT_PANTRY, get_section, normalize

conn = get_connection()
init_db(conn)

st.title("Welcome! Ready to plan some meals?")
st.markdown("Here's what you can do:")

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
if st.button("Plan my meals", type="primary", icon=":material/arrow_forward:"):
    save_user_settings(conn, 4, 5)
    for name in DEFAULT_PANTRY:
        add_pantry_item(conn, name, normalize(name), get_section(name))
    st.switch_page("pages/7_preferences.py")
