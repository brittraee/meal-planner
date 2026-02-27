"""Pantry manager — add, remove, and browse common ingredients."""

import streamlit as st

from src.database import (
    add_pantry_item,
    delete_pantry_item,
    get_connection,
    get_pantry_items,
    init_db,
)
from src.ingredients import get_ingredients_by_section, get_section, normalize

st.title("Pantry Manager")
st.caption(
    "Track what you keep on hand. "
    "Pantry items are automatically skipped on shopping lists."
)

conn = get_connection()
init_db(conn)

# --- Sidebar: workflow guide ---
with st.sidebar:
    st.markdown("### Quick Start")
    st.caption(
        "Add what you keep on hand. "
        "These get skipped on shopping lists."
    )
    st.page_link(
        "pages/3_shopping.py",
        label="Shopping List",
        icon=":material/shopping_cart:",
    )

# --- Current pantry ---
items = get_pantry_items(conn)
current_names = {i["normalized_name"] for i in items}

if items:
    st.subheader(f"Your Pantry ({len(items)} items)")

    # Group by category
    by_cat: dict[str, list[dict]] = {}
    for item in items:
        by_cat.setdefault(item["category"].title(), []).append(item)

    for category in sorted(by_cat):
        st.markdown(f"**{category}**")
        cat_items = by_cat[category]
        # Render as rows with remove buttons
        for row_start in range(0, len(cat_items), 4):
            row = cat_items[row_start : row_start + 4]
            cols = st.columns(4)
            for col, item in zip(cols, row, strict=False):
                with col:
                    if st.button(
                        f"{item['name']}  \u00d7",
                        key=f"del_{item['id']}",
                        use_container_width=True,
                        type="secondary",
                    ):
                        delete_pantry_item(conn, item["id"])
                        st.rerun()
else:
    st.info(
        "Your pantry is empty. Add items you keep on hand — "
        "they'll be skipped on shopping lists so you only buy what you need."
    )

# --- Add from common ingredients ---
st.divider()
st.subheader("Add Items")

sections = get_ingredients_by_section()
tabs = st.tabs(list(sections.keys()))

for tab, (section, section_items) in zip(
    tabs, sections.items(), strict=False
):
    with tab:
        # Filter out items already in pantry
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
                    add_pantry_item(
                        conn, item, normalize(item), get_section(item)
                    )
                st.rerun()
        else:
            st.caption("All items from this section are in your pantry.")

# --- Custom item ---
st.divider()
with st.form("add_custom_item"):
    col1, col2 = st.columns([3, 1])
    custom_name = col1.text_input(
        "Add something else",
        placeholder="e.g. Tahini, Gochujang, Miso paste",
    )
    col2.markdown("<br>", unsafe_allow_html=True)
    submitted = col2.form_submit_button("Add", use_container_width=True)

if submitted and custom_name.strip():
    add_pantry_item(
        conn,
        custom_name.strip(),
        normalize(custom_name.strip()),
        get_section(custom_name.strip()),
    )
    st.rerun()
