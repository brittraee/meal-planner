"""Meal plan generator with scoring evidence and tag priorities."""

from datetime import date

import streamlit as st

from src.database import (
    create_meal_plan,
    get_connection,
    get_unique_tags,
    get_user_settings,
    init_db,
)
from src.planner import DAY_LABELS, generate_plan, pick_replacement

st.title("Meal Planner")
st.caption(
    "Generate a balanced meal plan. Pin recipes from the Recipe Browser, "
    "or let the planner choose for you."
)

conn = get_connection()
init_db(conn)

# Load user preferences from onboarding
_settings = get_user_settings(conn)
_default_days = _settings["meals_per_week"] if _settings else 5

# --- Inline plan settings ---

days_col, start_col, tags_col = st.columns([1.5, 1.5, 3])
with days_col:
    num_days = st.slider("Days to plan", min_value=3, max_value=7, value=_default_days)
with start_col:
    start_day = st.selectbox("Start day", DAY_LABELS)
with tags_col:
    available_tags = [t for t in get_unique_tags(conn) if not t.rstrip("min").isdigit()]
    priority_tags = st.multiselect(
        "Prioritize tags",
        options=available_tags,
        help="Recipes with these tags score higher (+2 each).",
    )

with st.expander("Advanced filters"):
    excl_col, incl_col = st.columns(2)
    with excl_col:
        excluded = st.text_input(
            "Exclude ingredients",
            placeholder="e.g. mushrooms, olives",
        )
    with incl_col:
        included = st.text_input(
            "Must include ingredients",
            placeholder="e.g. chicken, rice",
        )
    require_included = st.toggle("Strict mode (only show exact matches)", value=False)
    seed = st.number_input("Random seed (0 = random)", min_value=0, value=0)

excluded_list = [x.strip() for x in excluded.split(",") if x.strip()] if excluded else None
included_list = [x.strip() for x in included.split(",") if x.strip()] if included else None

# --- Pinned recipes section ---
pinned = st.session_state.get("pinned_recipes", {})
pinned_any: list[str] = []
pinned_fixed: list[tuple[int, str]] = []

if pinned:
    day_labels_for_plan = [
        DAY_LABELS[(DAY_LABELS.index(start_day) + i) % 7] for i in range(num_days)
    ]
    day_options = ["Any day", *day_labels_for_plan]

    with st.expander(f"Pinned recipes ({len(pinned)})", expanded=True):
        for recipe_id, title in pinned.items():
            col_title, col_day, col_remove = st.columns([3, 2, 1])
            with col_title:
                st.markdown(f"**{title}**")
            with col_day:
                choice = st.selectbox(
                    "Day",
                    options=day_options,
                    key=f"pin_day_{recipe_id}",
                    label_visibility="collapsed",
                )
            with col_remove:
                if st.button("Remove", key=f"pin_remove_{recipe_id}"):
                    del st.session_state.pinned_recipes[recipe_id]
                    st.rerun()

            if choice == "Any day":
                pinned_any.append(recipe_id)
            else:
                day_idx = day_labels_for_plan.index(choice)
                pinned_fixed.append((day_idx, recipe_id))

        if len(pinned) > num_days:
            st.warning(
                f"You have {len(pinned)} pins but only {num_days} days. "
                "Some may be dropped."
            )

# --- Generate plan ---
if st.button("Generate Plan", type="primary", use_container_width=True):
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
            pinned_fixed=pinned_fixed if pinned_fixed else None,
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
    header = st.columns([2, 3, 2, 1.5, 1])
    header[0].markdown("**Day**")
    header[1].markdown("**Recipe**")
    header[2].markdown("**Protein**")
    header[3].markdown("**Servings**")
    header[4].markdown("")

    # Display table with servings adjustment, swap, and scoring evidence
    for idx, row in plan_df.iterrows():
        cols = st.columns([2, 3, 2, 1.5, 1])
        with cols[0]:
            st.markdown(f"**{row['day_label']}**")
        with cols[1]:
            st.markdown(row["title"])
        with cols[2]:
            st.markdown(f"_{row['protein']}_")
        with cols[3]:
            new_servings = st.number_input(
                "Servings",
                min_value=1,
                max_value=20,
                value=int(row.get("servings", 4) or 4),
                key=f"servings_{idx}",
                label_visibility="collapsed",
            )
            plan_df.at[idx, "servings"] = new_servings
        with cols[4]:
            if st.button("Swap", key=f"swap_{idx}"):
                replacement = pick_replacement(conn, plan_df, idx)
                for col in replacement:
                    plan_df.at[idx, col] = replacement[col]
                st.session_state["current_plan"] = plan_df
                st.rerun()

        # Scoring evidence (below each recipe row)
        evidence_parts = []
        pantry = row.get("pantry_matches", "")
        tags = row.get("tag_bonuses", "")
        if pantry:
            evidence_parts.append(f"Uses pantry: {pantry}")
        if tags and tags not in ("pinned", "swapped"):
            evidence_parts.append(f"Tags: {tags}")
        elif tags == "pinned":
            evidence_parts.append("Pinned by you")
        elif tags == "swapped":
            evidence_parts.append("Swapped in")
        if evidence_parts:
            st.caption(" · ".join(evidence_parts))

    # Prep notes (fall back to truncated instructions if no prep notes)
    with st.expander("View prep notes"):
        for _, row in plan_df.iterrows():
            st.markdown(f"**{row['day_label']} — {row['title']}**")
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
        st.success(f"**{plan_name}** saved!")
        del st.session_state["current_plan"]
        st.rerun()
