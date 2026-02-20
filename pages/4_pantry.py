"""Pantry manager — add, remove, and import pantry items."""

from pathlib import Path

import pandas as pd
import streamlit as st

from src.database import (
    add_pantry_item,
    delete_pantry_item,
    get_connection,
    get_pantry_items,
    init_db,
)
from src.ingredients import normalize

st.title("Pantry Manager")

conn = get_connection()
init_db(conn)

# --- Current pantry ---
items = get_pantry_items(conn)

if items:
    st.subheader(f"Current Pantry ({len(items)} items)")

    df = pd.DataFrame(items)
    for category in sorted(df["category"].unique()):
        st.markdown(f"**{category.title()}**")
        cat_items = df[df["category"] == category]
        for _, item in cat_items.iterrows():
            col1, col2 = st.columns([4, 1])
            col1.markdown(f"- {item['name']}")
            if col2.button("Remove", key=f"del_{item['id']}"):
                delete_pantry_item(conn, item["id"])
                st.rerun()
else:
    st.info("Pantry is empty. Add items below or import from YAML.")

# --- Add item ---
st.subheader("Add Item")
with st.form("add_pantry_item"):
    col1, col2 = st.columns(2)
    name = col1.text_input("Item name")
    category = col2.selectbox("Category", ["staples", "fresh", "protein", "dairy", "frozen"])

    if st.form_submit_button("Add"):
        if name.strip():
            add_pantry_item(conn, name.strip(), normalize(name.strip()), category)
            st.success(f"Added: {name}")
            st.rerun()
        else:
            st.warning("Enter an item name.")

# --- Import from YAML ---
st.subheader("Import from YAML")
yaml_path = Path("examples/pantry.yaml")
if yaml_path.exists():
    if st.button("Import from examples/pantry.yaml"):
        import yaml

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        count = 0
        for cat, items_list in data.items():
            if isinstance(items_list, list):
                for item in items_list:
                    add_pantry_item(conn, item, normalize(item), cat)
                    count += 1

        st.success(f"Imported {count} items from pantry.yaml")
        st.rerun()
else:
    st.info("No pantry.yaml found in examples/")
