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

PAGE_SIZE = 50

# --- Custom CSS for compact rows ---
st.markdown(
    """
    <style>
    /* Vertical-center all column rows */
    div[data-testid="stHorizontalBlock"] {
        align-items: center;
    }
    /* Compress vertical gap between consecutive rows */
    .recipe-rows div[data-testid="stHorizontalBlock"] {
        margin-top: -0.6rem;
        margin-bottom: -0.6rem;
    }
    /* Compact detail panel */
    .detail-panel [data-testid="stVerticalBlockBorderWrapper"] > div {
        padding: 0.5rem 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Recipe Browser")

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

# --- Sidebar filters ---
with st.sidebar:
    st.subheader("Filters")

    available_tags = get_unique_tags(conn)
    selected_tags = st.multiselect("Tags", available_tags)

    search_text = st.text_input("Search recipes", placeholder="e.g. chicken, pasta...")

# --- Inline filter bar ---
proteins = get_unique_proteins(conn)
time_options = ["Any time", "15 min", "30 min", "45 min", "60 min", "90 min", "120 min"]
time_values = {"Any time": None, "15 min": 15, "30 min": 30, "45 min": 45, "60 min": 60, "90 min": 90, "120 min": 120}

filter_col1, filter_col2, filter_spacer = st.columns([1.5, 1.5, 4])
with filter_col1:
    selected_protein = st.selectbox(
        "Protein",
        ["All proteins", *proteins],
        label_visibility="collapsed",
    )
with filter_col2:
    selected_time = st.selectbox(
        "Cook time",
        time_options,
        label_visibility="collapsed",
    )

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

# --- Detail panel (master-detail) ---
if "viewing_recipe" in st.session_state:
    viewing_id = st.session_state.viewing_recipe
    details = get_recipe_details(conn, viewing_id)
    if details:
        with st.container(border=True):
            close_col, title_col = st.columns([0.5, 5])
            with close_col:
                if st.button("X", key="close_detail"):
                    del st.session_state["viewing_recipe"]
                    st.rerun()
            with title_col:
                st.markdown(f"### {details['title']}")

            info_col, ing_col = st.columns(2)
            with info_col:
                st.markdown(f"**Protein:** {details['protein']}")
                st.markdown(f"**Servings:** {details.get('servings') or 4}")
                if details.get("prep_notes"):
                    st.markdown(f"**Prep:** {details['prep_notes']}")
                if details.get("tags"):
                    tag_html = " ".join(
                        f'<span style="background:rgba(128,128,128,0.12);border-radius:4px;'
                        f'padding:2px 8px;font-size:0.75rem">{t}</span>'
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
                        qty_str = str(int(q)) if q == int(q) else f"{q:.2f}".rstrip("0").rstrip(".")
                        if ing.get("unit"):
                            qty_str = f"{qty_str} {ing['unit']}"
                        qty_str += " "
                    lines.append(f"- {qty_str}{ing['raw_text']}{optional}")
                st.markdown("**Ingredients:**\n" + "\n".join(lines))

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

# --- Column headers ---
hdr = st.columns([0.4, 3, 1.2, 2.5, 0.5])
with hdr[1]:
    st.caption("Recipe")
with hdr[2]:
    st.caption("Protein")
with hdr[3]:
    st.caption("Tags")
st.divider()

# --- Recipe rows ---
if page_results:
    st.markdown('<div class="recipe-rows">', unsafe_allow_html=True)

    for recipe in page_results:
        is_pinned = recipe["id"] in pinned
        recipe_id = recipe["id"]

        row = st.columns([0.4, 3, 1.2, 2.5, 0.5])

        with row[0]:
            checked = st.checkbox(
                "pin",
                value=is_pinned,
                key=f"pin_{recipe_id}",
                label_visibility="collapsed",
            )
            if checked and not is_pinned:
                st.session_state.pinned_recipes[recipe_id] = recipe["title"]
                st.rerun()
            elif not checked and is_pinned:
                del st.session_state.pinned_recipes[recipe_id]
                st.rerun()

        with row[1]:
            pin_dot = '<span style="color:#4CAF50">&#9679; </span>' if is_pinned else ""
            title_text = f"<b>{recipe['title']}</b>" if is_pinned else recipe["title"]
            st.markdown(f"{pin_dot}{title_text}", unsafe_allow_html=True)

        with row[2]:
            st.caption(recipe["protein"])

        with row[3]:
            if recipe.get("tags"):
                tags_html = " ".join(
                    f'<span style="background:rgba(128,128,128,0.1);border-radius:4px;'
                    f'padding:1px 5px;font-size:0.65rem;white-space:nowrap">{t}</span>'
                    for t in recipe["tags"]
                )
                st.markdown(tags_html, unsafe_allow_html=True)

        with row[4]:
            if st.button("...", key=f"view_{recipe_id}"):
                st.session_state.viewing_recipe = recipe_id
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

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
