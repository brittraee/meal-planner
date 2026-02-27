"""Add recipes via URL import or manual entry."""

import re

import streamlit as st

from src.database import (
    get_connection,
    get_unique_proteins,
    get_unique_tags,
    init_db,
    insert_recipe_dict,
)
from src.scraper import scrape_recipe

st.title("Add Recipe")
st.caption("Import from a URL or add one manually.")

conn = get_connection()
init_db(conn)

# --- Sidebar: workflow guide ---
with st.sidebar:
    st.markdown("### Quick Start")
    st.caption(
        "Paste a URL to auto-import, or add one manually. "
        "New recipes show up in the library right away."
    )
    st.page_link(
        "pages/1_recipes.py",
        label="Recipe Library",
        icon=":material/menu_book:",
    )

tab_url, tab_manual = st.tabs(["Import from URL", "Manual Entry"])

# ---- Tab 1: URL Import ----
with tab_url:
    st.caption("Paste a recipe URL and we'll pull in the title, ingredients, and image.")
    url = st.text_input("Recipe URL", placeholder="https://www.allrecipes.com/recipe/...")

    if st.button("Scrape Recipe", type="primary", disabled=not url):
        try:
            with st.spinner("Scraping..."):
                data = scrape_recipe(url)
            st.session_state["scraped_recipe"] = data
        except Exception as e:
            st.error(f"Could not scrape that URL: {e}")

    if "scraped_recipe" in st.session_state:
        data = st.session_state["scraped_recipe"]

        st.subheader("Preview")
        if data["image_url"]:
            st.image(data["image_url"], width=300)

        data["title"] = st.text_input("Title", value=data["title"], key="url_title")
        data["servings"] = st.number_input(
            "Servings", min_value=1, max_value=20, value=data["servings"], key="url_servings"
        )

        # Protein selector
        proteins = get_unique_proteins(conn)
        protein_options = ["unknown", *proteins]
        data["protein"] = st.selectbox(
            "Protein",
            protein_options,
            index=0,
            key="url_protein",
        )

        # Editable ingredients
        st.markdown("**Ingredients:**")
        for ing in data["ingredients"]:
            st.text(f"  {ing['raw_text']}")

        # Tags
        existing_tags = get_unique_tags(conn)
        selected_tags = st.multiselect(
            "Tags", existing_tags, default=data.get("tags", []), key="url_tags"
        )
        new_tags = st.text_input("Additional tags (comma-separated)", key="url_new_tags")
        if new_tags:
            selected_tags.extend(t.strip().lower() for t in new_tags.split(",") if t.strip())
        data["tags"] = selected_tags

        if st.button("Save Recipe", key="save_url"):
            # Regenerate ID from possibly edited title
            slug = re.sub(r"[^a-z0-9]+", "_", data["title"].lower()).strip("_")
            data["id"] = f"url_{slug}"
            insert_recipe_dict(conn, data)
            conn.commit()
            st.success(f"Saved **{data['title']}**!")
            del st.session_state["scraped_recipe"]
            st.rerun()

# ---- Tab 2: Manual Entry ----
with tab_manual:
    st.caption("Add a recipe by hand — fill in what you have, skip what you don't.")
    title = st.text_input("Recipe title", key="manual_title")
    servings = st.number_input(
        "Servings", min_value=1, max_value=20, value=4, key="manual_servings"
    )
    prep_notes = st.text_area("Prep notes", key="manual_prep", height=80)

    # Protein
    proteins = get_unique_proteins(conn)
    protein = st.selectbox("Protein", ["unknown", *proteins], key="manual_protein")

    # Dynamic ingredients
    st.markdown("**Ingredients**")
    header_cols = st.columns([1, 1, 3])
    header_cols[0].caption("Qty")
    header_cols[1].caption("Unit")
    header_cols[2].caption("Ingredient")
    if "manual_ingredient_count" not in st.session_state:
        st.session_state["manual_ingredient_count"] = 3

    ingredients = []
    row_to_remove = None
    for i in range(st.session_state["manual_ingredient_count"]):
        cols = st.columns([1, 1, 3, 0.4])
        with cols[0]:
            qty = st.text_input("Qty", key=f"ing_qty_{i}", label_visibility="collapsed",
                                placeholder="Qty")
        with cols[1]:
            unit = st.text_input("Unit", key=f"ing_unit_{i}", label_visibility="collapsed",
                                 placeholder="Unit")
        with cols[2]:
            name = st.text_input("Ingredient", key=f"ing_name_{i}", label_visibility="collapsed",
                                 placeholder="Ingredient name")
        with cols[3]:
            if st.session_state["manual_ingredient_count"] > 1 and st.button(
                "✕", key=f"ing_del_{i}"
            ):
                row_to_remove = i
        if name:
            parsed_qty = None
            if qty:
                try:
                    if "/" in qty:
                        num, denom = qty.split("/")
                        parsed_qty = float(num) / float(denom)
                    else:
                        parsed_qty = float(qty)
                except ValueError:
                    pass

            raw = f"{qty} {unit} {name}".strip() if qty else name
            ingredients.append({
                "raw_text": raw,
                "normalized_name": name.lower().strip(),
                "is_optional": False,
                "qty": parsed_qty,
                "unit": unit.strip() or None,
            })

    if row_to_remove is not None:
        # Shift values from rows above the removed one down
        count = st.session_state["manual_ingredient_count"]
        for j in range(row_to_remove, count - 1):
            for field in ("qty", "unit", "name"):
                src_key = f"ing_{field}_{j + 1}"
                dst_key = f"ing_{field}_{j}"
                st.session_state[dst_key] = st.session_state.get(src_key, "")
        # Clear the last row's keys
        for field in ("qty", "unit", "name"):
            st.session_state.pop(f"ing_{field}_{count - 1}", None)
        st.session_state["manual_ingredient_count"] = count - 1
        st.rerun()

    if st.button("+ Add ingredient row"):
        st.session_state["manual_ingredient_count"] += 1
        st.rerun()

    # Instructions
    instructions = st.text_area("Instructions", key="manual_instructions", height=150)

    # Tags
    existing_tags = get_unique_tags(conn)
    tags = st.multiselect("Tags", existing_tags, key="manual_tags")
    new_tags = st.text_input("Additional tags (comma-separated)", key="manual_new_tags")
    if new_tags:
        tags.extend(t.strip().lower() for t in new_tags.split(",") if t.strip())

    if st.button("Save Recipe", type="primary", key="save_manual", disabled=not title):
        slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
        recipe_data = {
            "id": f"manual_{slug}",
            "title": title,
            "protein": protein,
            "prep_notes": prep_notes,
            "servings": servings,
            "source_type": "manual",
            "instructions": instructions,
            "ingredients": ingredients,
            "tags": tags,
        }
        insert_recipe_dict(conn, recipe_data)
        conn.commit()
        st.success(f"Saved **{title}**!")
        # Reset form
        st.session_state["manual_ingredient_count"] = 3
        st.rerun()
