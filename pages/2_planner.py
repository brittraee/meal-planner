"""Meal plan generator with scoring evidence and tag priorities."""

from datetime import date

import streamlit as st

from src.database import (
    create_meal_plan,
    get_connection,
    get_unique_proteins,
    get_unique_tags,
    get_user_settings,
    init_db,
    search_recipes,
)
from src.planner import generate_plan, pick_replacement

st.title("Meal Planner")
st.caption(
    "Generate a balanced week of dinners. "
    "Pin favorites or let the planner choose."
)

conn = get_connection()
init_db(conn)

# --- Sidebar: recipe search + workflow guide ---
with st.sidebar:
    st.markdown("### Find & Pin Recipes")
    _search_q = st.text_input(
        "Search recipes",
        placeholder="e.g. chicken, pasta",
        key="planner_search",
        label_visibility="collapsed",
    )
    if _search_q:
        _results = search_recipes(conn, query=_search_q)
        if _results:
            for r in _results[:8]:
                col_title, col_pin = st.columns([3, 1])
                with col_title:
                    st.caption(f"**{r['title']}** · {r['protein']}")
                with col_pin:
                    _pinned = st.session_state.get("pinned_recipes", {})
                    if r["id"] not in _pinned:
                        if st.button(
                            "\U0001f4cc", key=f"sb_pin_{r['id']}",
                            help=f"Pin {r['title']}",
                        ):
                            st.session_state.setdefault("pinned_recipes", {})[r["id"]] = r["title"]
                            st.rerun()
                    else:
                        st.caption("\u2713")
        else:
            st.caption("No matches.")

    st.divider()
    st.markdown("### Quick Start")
    st.caption(
        "Generate → swap any meal → adjust servings → save. "
        "Pin recipes from the library to lock them in."
    )
    st.page_link(
        "pages/1_recipes.py",
        label="Browse Recipe Library",
        icon=":material/menu_book:",
    )

# Load user preferences from onboarding
_settings = get_user_settings(conn)
_default_days = _settings["meals_per_week"] if _settings else 5
_default_servings = _settings["servings"] if _settings else 4

# --- Inline plan settings ---

num_days = st.slider("Meals to plan", min_value=3, max_value=7, value=_default_days)
start_day = "Monday"  # kept for internal ordering, not shown to user

with st.expander("Customize"):
    # Tag priorities as checkboxes
    available_tags = [t for t in get_unique_tags(conn) if not t.rstrip("min").isdigit()]
    # Group into lifestyle vs cuisine
    lifestyle_tags = [
        t for t in available_tags if t in {
            "quick", "comfortfood", "kidfriendly", "batchcook", "onepan",
            "healthy", "spicy", "sheetpan", "breakfastfordinner", "cheesy",
            "casserole", "bbq", "soup", "salad", "bowl", "sidedish", "bake",
            "skillet", "chili", "tacos", "lowcarb", "vegan", "paleo", "keto",
            "whole30",
        }
    ]
    st.markdown("**Prioritize tags** — selected tags score higher")
    priority_tags = st.pills(
        "Priority tags",
        options=lifestyle_tags,
        selection_mode="multi",
        key="priority_tag_pills",
        label_visibility="collapsed",
    ) or []

    st.divider()
    st.markdown(
        "**Include / exclude ingredients** — "
        "tap once to include, twice to exclude, again to clear"
    )

    # Build ingredient list from proteins + common staples
    _proteins = get_unique_proteins(conn)
    _staples = ["rice", "pasta", "potato", "broccoli", "spinach", "mushroom",
                 "cheese", "tortilla", "noodles", "tofu"]
    _selector_items = _proteins + [s for s in _staples if s not in _proteins]

    # Tri-state: None → "include" → "exclude" → None
    if "ing_states" not in st.session_state:
        st.session_state.ing_states = {}

    _cols = st.columns(5)
    for _i, _ing in enumerate(_selector_items):
        _state = st.session_state.ing_states.get(_ing)
        if _state == "include":
            _label = f"+ {_ing}"
            _type = "primary"
        elif _state == "exclude":
            _label = f"× {_ing}"
            _type = "secondary"
        else:
            _label = _ing
            _type = "tertiary"

        with _cols[_i % 5]:
            if st.button(_label, key=f"ing_{_ing}", type=_type, use_container_width=True):
                if _state is None:
                    st.session_state.ing_states[_ing] = "include"
                elif _state == "include":
                    st.session_state.ing_states[_ing] = "exclude"
                else:
                    del st.session_state.ing_states[_ing]
                st.rerun()

    seed = 0

_ing_states = st.session_state.get("ing_states", {})
included_list = [k for k, v in _ing_states.items() if v == "include"] or None
excluded_list = [k for k, v in _ing_states.items() if v == "exclude"] or None
require_included = bool(included_list)

# --- Pinned recipes section ---
pinned = st.session_state.get("pinned_recipes", {})
pinned_any: list[str] = []

if pinned:
    with st.expander(f"Pinned recipes ({len(pinned)})", expanded=True):
        for recipe_id, title in pinned.items():
            col_title, col_remove = st.columns([5, 1])
            with col_title:
                st.markdown(f"**{title}**")
            with col_remove:
                if st.button("Remove", key=f"pin_remove_{recipe_id}"):
                    del st.session_state.pinned_recipes[recipe_id]
                    st.rerun()
            pinned_any.append(recipe_id)

        if len(pinned) > num_days:
            st.warning(
                f"You have {len(pinned)} pins but only {num_days} meals. "
                "Some may be dropped."
            )
else:
    st.caption(
        "No pinned recipes — the planner will pick for you. "
        "Or pin specific recipes from the Recipe Library."
    )

# --- Generate plan ---
if st.button("Generate Plan", type="secondary", use_container_width=True):
    try:
        plan_df = generate_plan(
            conn,
            days=num_days,
            excluded_ingredients=excluded_list,
            included_ingredients=included_list,
            require_included=require_included,
            seed=seed if seed > 0 else None,
            start_day=start_day,
            pinned_any=pinned_any if pinned_any else None,
            priority_tags=priority_tags if priority_tags else None,
        )
        st.session_state["current_plan"] = plan_df
        # Clear pins after generating
        st.session_state.pinned_recipes = {}
    except ValueError as e:
        st.error(str(e))

# --- Display plan ---
if "current_plan" in st.session_state:
    plan_df = st.session_state["current_plan"]

    st.divider()
    st.subheader("Your Meal Plan")

    # Column headers
    header = st.columns([1.5, 3, 1.5, 2.5, 2.5, 1.2, 0.8])
    header[0].markdown("**#**")
    header[1].markdown("**Recipe**")
    header[2].markdown("**Protein**")
    header[3].markdown("\U0001f3ea **Pantry**")
    header[4].markdown("\U0001f3f7\ufe0f **Tags**")
    header[5].markdown("**Servings**")
    header[6].markdown("")

    # Display table with scoring evidence inline
    for idx, row in plan_df.iterrows():
        cols = st.columns([1.5, 3, 1.5, 2.5, 2.5, 1.2, 0.8])
        with cols[0]:
            st.markdown(f"**Meal {idx + 1}**")
        with cols[1]:
            st.markdown(row["title"])
        with cols[2]:
            st.markdown(f"_{row['protein']}_")
        with cols[3]:
            pantry = row.get("pantry_matches", "")
            if pantry:
                st.caption(pantry)
        with cols[4]:
            tags = row.get("tag_bonuses", "")
            if tags and tags not in ("pinned", "swapped"):
                st.caption(tags)
            elif tags == "pinned":
                st.caption("\U0001f4cc pinned")
            elif tags == "swapped":
                st.caption("\U0001f500 swapped")
        with cols[5]:
            new_servings = st.number_input(
                "Servings",
                min_value=1,
                max_value=20,
                value=_default_servings,
                key=f"servings_{idx}",
                label_visibility="collapsed",
            )
            plan_df.at[idx, "servings"] = new_servings
        with cols[6]:
            if st.button("\U0001f500", key=f"swap_{idx}"):
                replacement = pick_replacement(conn, plan_df, idx)
                for col in replacement:
                    plan_df.at[idx, col] = replacement[col]
                st.session_state["current_plan"] = plan_df
                st.rerun()

    # Prep notes (fall back to truncated instructions if no prep notes)
    with st.expander("View prep notes"):
        for _, row in plan_df.iterrows():
            st.markdown(f"**{row['title']}**")
            notes = row.get("prep_notes") or ""
            if not notes.strip():
                result = conn.execute(
                    "SELECT instructions FROM recipes WHERE id = ?",
                    (row["recipe_id"],),
                ).fetchone()
                if result and result["instructions"]:
                    # Show first 2 sentences as a quick summary
                    text = result["instructions"].strip()
                    sentences = text.replace("\r\n", " ").replace("\n", " ").split(". ")
                    notes = ". ".join(sentences[:2]).strip()
                    if not notes.endswith("."):
                        notes += "."
            if notes.strip():
                st.markdown(f"_{notes}_")
            st.markdown("---")

    # --- Save plan ---
    st.divider()
    st.subheader("Save Plan")
    save_col1, save_col2 = st.columns(2)
    with save_col1:
        plan_name = st.text_input(
            "Plan name",
            value=f"Week of {date.today().strftime('%b %d')}",
        )
    with save_col2:
        plan_date = st.date_input("Start date", value=date.today())

    if st.button("Save Plan"):
        meals = [
            (int(row["day"]), row["day_label"], row["recipe_id"], int(row["servings"]))
            for _, row in plan_df.iterrows()
        ]
        create_meal_plan(conn, plan_name, str(plan_date), meals)
        st.session_state["plan_just_saved"] = True
        del st.session_state["current_plan"]
        st.rerun()

    if st.session_state.pop("plan_just_saved", False):
        st.success(f"Plan saved!")
        st.page_link(
            "pages/3_shopping.py",
            label="View Shopping List",
            icon=":material/shopping_cart:",
        )
