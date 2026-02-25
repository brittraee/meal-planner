"""Recipe browser with search, tag filter, and protein filter."""

import streamlit as st

from src.database import (
    get_connection,
    get_recipe_details,
    get_unique_proteins,
    get_unique_tags,
    init_db,
    search_recipes,
)

PAGE_SIZE = 75

# --- Custom CSS for compact rows ---
st.markdown(
    """
    <style>
    /* Left-align clickable recipe titles in cards */
    [data-testid="stBaseButton-tertiary"] button {
        text-align: left;
        justify-content: flex-start;
        font-size: 1.05rem;
    }
    /* Make recipe cards feel clickable */
    [data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stBaseButton-tertiary"]) {
        cursor: pointer;
        transition: background-color 0.15s ease, border-color 0.15s ease;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stBaseButton-tertiary"]):hover {
        background-color: rgba(128, 128, 128, 0.08);
        border-color: rgba(128, 128, 128, 0.3);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Recipe Browser")
st.caption("Click any recipe to see ingredients and prep details. Pin recipes to lock them into your plan, or let the Meal Planner shuffle and pick for you.")

conn = get_connection()
init_db(conn)

# --- Pinned recipes (session state) ---
if "pinned_recipes" not in st.session_state:
    st.session_state.pinned_recipes = {}  # {recipe_id: title}

pinned = st.session_state.pinned_recipes

# Check if recipes exist
all_recipes = search_recipes(conn)
if not all_recipes:
    st.warning("No recipes found. Run `python scripts/ingest.py` to import your recipe cards.")
    st.stop()

# --- Filter bar ---
proteins = get_unique_proteins(conn)
available_tags = [t for t in get_unique_tags(conn) if not t.rstrip("min").isdigit()]
time_options = ["Any time", "15 min", "30 min", "45 min", "60 min", "90 min", "120 min"]
time_values = {"Any time": None, "15 min": 15, "30 min": 30, "45 min": 45, "60 min": 60, "90 min": 90, "120 min": 120}

protein_col, time_col, tags_col, spacer, search_col = st.columns([1.5, 1.5, 2.5, 0.5, 2])
with protein_col:
    selected_protein = st.selectbox(
        "Protein Type",
        ["All proteins", *proteins],
    )
with time_col:
    selected_time = st.selectbox(
        "Prep/Cook Time",
        time_options,
    )
with tags_col:
    selected_tags = st.multiselect("Tags", available_tags)
with search_col:
    search_text = st.text_input("Search", placeholder="e.g. chicken, pasta...")

max_time = time_values[selected_time]

# --- Query recipes ---
results = search_recipes(
    conn,
    query=search_text or None,
    tags=selected_tags or None,
    protein=selected_protein if selected_protein != "All proteins" else None,
    max_time=max_time,
)

# --- Pinned summary bar ---
if pinned:
    col_info, col_clear = st.columns([5, 1])
    with col_info:
        names = ", ".join(pinned.values())
        st.success(f"**{len(pinned)}** pinned: {names}")
    with col_clear:
        if st.button("Clear all", key="clear_pins"):
            st.session_state.pinned_recipes = {}
            st.rerun()

# --- Pagination ---
total = len(results)
if "recipe_page" not in st.session_state:
    st.session_state.recipe_page = 0

# Reset page when filters change
filter_key = f"{search_text}|{selected_tags}|{selected_protein}|{selected_time}"
if st.session_state.get("_filter_key") != filter_key:
    st.session_state.recipe_page = 0
    st.session_state._filter_key = filter_key

page = st.session_state.recipe_page
total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
page = min(page, total_pages - 1)
start = page * PAGE_SIZE
page_results = results[start : start + PAGE_SIZE]

st.caption(f"{start + 1}–{min(start + PAGE_SIZE, total)} of {total}")

# --- Recipe card grid ---
COLS_PER_ROW = 4

if page_results:
    # Process cards in rows of 4
    for row_start in range(0, len(page_results), COLS_PER_ROW):
        row_recipes = page_results[row_start : row_start + COLS_PER_ROW]
        cols = st.columns(COLS_PER_ROW)

        for col, recipe in zip(cols, row_recipes):
            is_pinned = recipe["id"] in pinned
            recipe_id = recipe["id"]

            with col:
                with st.container(border=True):
                    is_viewing = st.session_state.get("viewing_recipe") == recipe_id
                    arrow = "▼" if is_viewing else "▶"
                    if st.button(
                        f"{arrow} {recipe['title']}",
                        key=f"view_{recipe_id}",
                        use_container_width=True,
                        type="tertiary",
                    ):
                        if st.session_state.get("viewing_recipe") == recipe_id:
                            del st.session_state["viewing_recipe"]
                        else:
                            st.session_state.viewing_recipe = recipe_id
                        st.rerun()

                    st.caption(recipe["protein"])
                    if recipe.get("tags"):
                        st.caption(", ".join(recipe["tags"]))

                    checked = st.checkbox(
                        "Pin",
                        value=is_pinned,
                        key=f"pin_{recipe_id}",
                    )
                    if checked and not is_pinned:
                        st.session_state.pinned_recipes[recipe_id] = recipe["title"]
                        st.rerun()
                    elif not checked and is_pinned:
                        del st.session_state.pinned_recipes[recipe_id]
                        st.rerun()

        # --- Inline detail panel (below the row that contains the clicked card) ---
        for recipe in row_recipes:
            if st.session_state.get("viewing_recipe") == recipe["id"]:
                details = get_recipe_details(conn, recipe["id"])
                if details:
                    with st.container(border=True):
                        info_col, ing_col = st.columns(2)
                        with info_col:
                            st.markdown(f"**Protein:** {details['protein']}")
                            st.markdown(f"**Servings:** {details.get('servings') or 4}")
                            if details.get("prep_notes"):
                                st.markdown(f"**Prep:** {details['prep_notes']}")
                            if details.get("tags"):
                                tag_html = " ".join(
                                    f'<span style="background:rgba(128,128,128,0.12);'
                                    f'border-radius:4px;padding:2px 8px;'
                                    f'font-size:0.75rem">{t}</span>'
                                    for t in details["tags"]
                                )
                                st.markdown(tag_html, unsafe_allow_html=True)
                        with ing_col:
                            lines = []
                            for ing in details["ingredients"]:
                                optional = " *(optional)*" if ing["is_optional"] else ""
                                qty_str = ""
                                if ing.get("qty"):
                                    q = ing["qty"]
                                    qty_str = (
                                        str(int(q))
                                        if q == int(q)
                                        else f"{q:.2f}".rstrip("0").rstrip(".")
                                    )
                                    if ing.get("unit"):
                                        qty_str = f"{qty_str} {ing['unit']}"
                                    qty_str += " "
                                lines.append(f"- {qty_str}{ing['raw_text']}{optional}")
                            st.markdown("**Ingredients:**\n" + "\n".join(lines))

    # --- Page navigation ---
    if total_pages > 1:
        prev_col, page_col, next_col = st.columns([1, 2, 1])
        with prev_col:
            if st.button("Previous", disabled=(page == 0), use_container_width=True):
                st.session_state.recipe_page = page - 1
                st.rerun()
        with page_col:
            st.markdown(
                f'<div style="text-align:center;padding-top:0.5rem">'
                f'Page {page + 1} of {total_pages}</div>',
                unsafe_allow_html=True,
            )
        with next_col:
            if st.button("Next", disabled=(page >= total_pages - 1), use_container_width=True):
                st.session_state.recipe_page = page + 1
                st.rerun()

else:
    st.info("No recipes match the current filters.")
