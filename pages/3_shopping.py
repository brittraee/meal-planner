"""Shopping list view with section grouping, checkboxes, and export."""

import streamlit as st

from src.database import (
    add_pantry_item,
    delete_pantry_item,
    get_connection,
    get_meal_plans,
    get_pantry_items,
    get_shopping_list,
    init_db,
)
from src.ingredients import get_ingredients_by_section, get_section, normalize
from src.shopping import (
    SECTION_ORDER,
    format_shopping_text,
    group_by_section,
)
from src.units import format_qty

st.title("Shopping List")
st.caption("Grouped by store section, pantry items filtered out.")

st.page_link(
    "pages/2_planner.py",
    label="Back to Plan",
    icon=":material/arrow_back:",
)

conn = get_connection()
init_db(conn)

# --- Sidebar: workflow guide ---
with st.sidebar:
    st.markdown("### Quick Start")
    st.caption(
        "Pick a plan, check off items as you shop. "
        "Pantry items are already filtered out."
    )
    st.page_link(
        "pages/4_pantry.py",
        label="Full Pantry Manager",
        icon=":material/grocery:",
    )


# --- Inline pantry editor dialog ---
@st.dialog("Quick Pantry Edit")
def _pantry_editor():
    """Add or remove pantry items without leaving the shopping list."""
    items = get_pantry_items(conn)
    current_names = {i["normalized_name"] for i in items}

    # Show current pantry with remove buttons
    if items:
        st.markdown(f"**Your Pantry ({len(items)} items)**")
        for item in items:
            col_name, col_del = st.columns([4, 1])
            with col_name:
                st.caption(item["name"])
            with col_del:
                if st.button("\u00d7", key=f"pdel_{item['id']}"):
                    delete_pantry_item(conn, item["id"])

    # Quick add from common ingredients
    st.divider()
    st.markdown("**Add items**")
    sections = get_ingredients_by_section()
    for section, section_items in sections.items():
        available = [i for i in section_items if normalize(i) not in current_names]
        if available:
            chosen = st.pills(
                section,
                options=available,
                selection_mode="multi",
                key=f"pdlg_{section}",
            )
            if chosen:
                for name in chosen:
                    add_pantry_item(conn, name, normalize(name), get_section(name))

# --- Quick pantry edit button ---
if st.button("Edit Pantry", icon=":material/edit:", type="tertiary"):
    _pantry_editor()

# --- Select plan ---
plans = get_meal_plans(conn)
if not plans:
    st.info(
        "No meal plans saved yet. Head to the **Meal Planner** to generate "
        "and save a plan — your shopping list will appear here."
    )
    st.page_link(
        "pages/2_planner.py",
        label="Go to Meal Planner",
        icon=":material/calendar_month:",
    )
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
        qty_str = format_qty(qty)
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

    _item_idx = 0
    sections = group_by_section(need_items)
    for section in SECTION_ORDER:
        if section not in sections:
            continue
        st.markdown(f"#### {section.title()}")
        for item in sections[section]:
            key = f"shop_{_item_idx}"
            _item_idx += 1
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

# --- Copy to clipboard ---
with st.expander("Copy to clipboard"):
    st.code(format_shopping_text(items), language=None)
