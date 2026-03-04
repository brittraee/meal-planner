"""Meal plan generator with scoring evidence and tag priorities."""

from datetime import date

import streamlit as st

from src.constants import PROTEIN_SUBS, TAG_DISPLAY
from src.database import (
    create_meal_plan,
    get_connection,
    get_meal_plans,
    get_unique_proteins,
    get_unique_tags,
    get_user_settings,
    init_db,
    search_recipes,
)
from src.planner import generate_plan, pick_replacement

st.title("Meal Planner")
st.markdown(
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
        "Generate → swap any meal → adjust servings → save."
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

_plan_col, _serv_col = st.columns(2)
with _plan_col:
    num_days = st.number_input(
        "Meals to plan", min_value=1, max_value=7, value=_default_days,
    )
with _serv_col:
    _default_servings = st.number_input(
        "Servings per meal", min_value=1, max_value=20, value=_default_servings,
    )
start_day = "Monday"  # kept for internal ordering, not shown to user

with st.expander("Customize", expanded=True):
    available_tags = [t for t in get_unique_tags(conn) if not t.rstrip("min").isdigit()]
    lifestyle_tags = [
        t for t in available_tags if t in {
            "quick", "comfortfood", "kidfriendly", "batchcook", "onepan",
            "healthy", "spicy", "sheetpan", "breakfast", "cheesy",
            "casserole", "bbq", "soup", "salad", "bowl", "sidedish", "bake",
            "skillet", "chili", "vegan", "paleo", "keto",
            "whole30",
        }
    ]
    st.markdown("**Prioritize tags** — selected tags score higher")
    priority_tags = st.pills(
        "Priority tags",
        options=lifestyle_tags,
        selection_mode="multi",
        format_func=lambda t: TAG_DISPLAY.get(t, t.title()),
        key="priority_tag_pills",
        label_visibility="collapsed",
    ) or []

    st.divider()

    # Build ingredient list from proteins + common staples
    _proteins = get_unique_proteins(conn)
    _staples = ["rice", "pasta", "potato", "broccoli", "spinach", "mushroom",
                 "cheese", "tortilla", "noodles"]
    _selector_items = _proteins + [s for s in _staples if s not in _proteins]

    st.markdown(":green[**Include**] — plan must include at least one recipe with selected ingredients")
    _included = st.pills(
        "Include ingredients",
        options=_selector_items,
        selection_mode="multi",
        format_func=str.title,
        key="include_pills",
        label_visibility="collapsed",
    ) or []

    # Sub-category refinement for selected proteins
    _sub_picks: list[str] = []
    for _ing in _included:
        if _ing in PROTEIN_SUBS:
            _subs = st.pills(
                f"{_ing.title()} type",
                options=PROTEIN_SUBS[_ing],
                selection_mode="multi",
                format_func=str.title,
                key=f"sub_{_ing}",
                label_visibility="collapsed",
            ) or []
            _sub_picks.extend(_subs)

    _excl_col, _ = st.columns([2, 3])
    with _excl_col:
        st.markdown(":red[**Exclude**] — recipes containing these items will be skipped")
        _exclude_text = st.text_input(
            "Exclude ingredients",
            placeholder="e.g. mushroom, shrimp",
            key="exclude_text",
            label_visibility="collapsed",
        )

    seed = 0

# Build final include list: use sub-picks where available, keep top-level otherwise
_final_included = []
for _ing in (_included or []):
    if _ing in PROTEIN_SUBS and _sub_picks:
        # Only keep sub-picks that belong to this protein
        _my_subs = [s for s in _sub_picks if s in PROTEIN_SUBS[_ing]]
        if _my_subs:
            _final_included.extend(_my_subs)
        else:
            _final_included.append(_ing)
    else:
        _final_included.append(_ing)

included_list = _final_included or None
excluded_list = (
    [x.strip().lower() for x in _exclude_text.split(",") if x.strip()]
    if _exclude_text else None
)
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
    st.caption("No pinned recipes — the planner will pick for you.")

# --- Generate plan ---
gen_col, clear_col = st.columns([3, 1])
with gen_col:
    _generate = st.button("Generate Plan", type="secondary", use_container_width=True)
with clear_col:
    if st.button("Start Fresh", use_container_width=True):
        for key in ["current_plan", "pinned_recipes", "checked_items", "checked_plan_id"]:
            st.session_state.pop(key, None)
        st.rerun()

if _generate:
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

# Auto-generate on first visit (no plan yet, no saved plans)
if "current_plan" not in st.session_state and not get_meal_plans(conn):
    try:
        plan_df = generate_plan(conn, days=num_days, start_day=start_day)
        st.session_state["current_plan"] = plan_df
    except ValueError:
        pass

# --- Display plan ---
if "current_plan" in st.session_state:
    plan_df = st.session_state["current_plan"]

    st.divider()
    st.subheader("Your Meal Plan")

    for idx, row in plan_df.iterrows():
        with st.container(border=True):
            st.markdown(f"**Meal {idx + 1}: {row['title']}**")
            meta = f"_{row['protein']}_"
            pantry = row.get("pantry_matches", "")
            if pantry:
                meta += f" · {pantry}"
            tags = row.get("tag_bonuses", "")
            if tags and tags not in ("pinned", "swapped"):
                meta += f" · {tags}"
            elif tags == "pinned":
                meta += " · pinned"
            elif tags == "swapped":
                meta += " · swapped"
            st.caption(meta)

            serv_col, swap_col = st.columns([3, 1])
            with serv_col:
                new_servings = st.number_input(
                    "Servings",
                    min_value=1,
                    max_value=20,
                    value=int(row["servings"]),
                    key=f"servings_{idx}",
                    label_visibility="collapsed",
                )
                plan_df.at[idx, "servings"] = new_servings
            with swap_col:
                if st.button("Swap", key=f"swap_{idx}", use_container_width=True):
                    replacement = pick_replacement(conn, plan_df, idx)
                    for col in replacement:
                        plan_df.at[idx, col] = replacement[col]
                    st.session_state["current_plan"] = plan_df
                    st.rerun()

    # --- Save & continue ---
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

    if st.button("Save & Continue to Shopping List", type="primary",
                  icon=":material/shopping_cart:", use_container_width=True):
        meals = [
            (int(row["day"]), row["day_label"], row["recipe_id"], int(row["servings"]))
            for _, row in plan_df.iterrows()
        ]
        create_meal_plan(conn, plan_name, str(plan_date), meals)
        del st.session_state["current_plan"]
        st.switch_page("pages/3_shopping.py")
