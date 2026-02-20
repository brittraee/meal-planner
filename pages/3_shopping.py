"""Shopping list view with section grouping, checkboxes, and export."""

import streamlit as st

from src.database import get_connection, get_meal_plans, get_shopping_list, init_db
from src.shopping import (
    SECTION_ORDER,
    format_shopping_json,
    format_shopping_markdown,
    format_shopping_text,
    group_by_section,
)

st.title("Shopping List")

conn = get_connection()
init_db(conn)

# --- Select plan ---
plans = get_meal_plans(conn)
if not plans:
    st.info("No meal plans saved yet. Create one in the Meal Planner page.")
    st.stop()

plan_options = {f"{p['name']} ({p['meal_count']} meals)": p["id"] for p in plans}
selected_plan_label = st.selectbox("Select a meal plan", list(plan_options.keys()))
plan_id = plan_options[selected_plan_label]

# --- Get shopping list ---
items = get_shopping_list(conn, plan_id)
if not items:
    st.info("No ingredients found for this plan.")
    st.stop()


def _display_name(item: dict) -> str:
    """Format item name with quantity when available."""
    qty = item.get("qty")
    unit = item.get("unit")
    name = item["normalized_name"]
    if qty:
        qty_str = str(int(qty)) if qty == int(qty) else f"{qty:.2f}".rstrip("0").rstrip(".")
        if unit:
            return f"{qty_str} {unit} {name}"
        return f"{qty_str} {name}"
    return item["display_name"]


# --- Display grouped by section ---
need_items = [i for i in items if not i["in_pantry"]]
have_items = [i for i in items if i["in_pantry"]]

st.subheader(f"Need to Buy ({len(need_items)} items)")
if need_items:
    if "checked_items" not in st.session_state:
        st.session_state["checked_items"] = set()

    sections = group_by_section(need_items)
    for section in SECTION_ORDER:
        if section not in sections:
            continue
        st.markdown(f"#### {section.title()}")
        for item in sections[section]:
            key = f"shop_{item['normalized_name']}"
            label = f"**{_display_name(item)}** — _{item['needed_for']}_"
            checked = st.checkbox(
                label,
                key=key,
                value=item["normalized_name"] in st.session_state["checked_items"],
            )
            if checked:
                st.session_state["checked_items"].add(item["normalized_name"])
            else:
                st.session_state["checked_items"].discard(item["normalized_name"])

if have_items:
    st.subheader(f"Already in Pantry ({len(have_items)} items)")
    for item in have_items:
        st.markdown(f"- ~~{_display_name(item)}~~")

# --- Copy & Export ---
st.subheader("Share & Export")

# Clipboard-friendly plain text (st.code renders with a built-in copy button)
with st.expander("Copy to clipboard"):
    st.code(format_shopping_text(items), language=None)

col1, col2 = st.columns(2)
with col1:
    md = format_shopping_markdown(items)
    st.download_button(
        "Download Markdown",
        data=md,
        file_name="shopping-list.md",
        mime="text/markdown",
    )
with col2:
    json_str = format_shopping_json(items)
    st.download_button(
        "Download JSON",
        data=json_str,
        file_name="shopping-list.json",
        mime="application/json",
    )
