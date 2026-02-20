"""Meal history and analytics dashboard."""

import pandas as pd
import streamlit as st

from src.database import (
    delete_meal_plan,
    get_all_recipes,
    get_connection,
    get_meal_plans,
    get_planned_meals,
    get_recipe_history,
    init_db,
)

st.title("Meal History & Analytics")

conn = get_connection()
init_db(conn)

# --- Past plans ---
plans = get_meal_plans(conn)
if not plans:
    st.info("No meal plans saved yet. Create one in the Meal Planner page.")
    st.stop()

st.subheader("Past Meal Plans")
for plan in plans:
    with st.expander(f"{plan['name']} — {plan['start_date'] or 'No date'}"):
        meals = get_planned_meals(conn, plan["id"])
        if meals:
            df = pd.DataFrame(meals)
            st.dataframe(
                df[["day_label", "title", "protein"]].rename(
                    columns={
                        "day_label": "Day",
                        "title": "Recipe",
                        "protein": "Protein",
                    }
                ),
                width="stretch",
                hide_index=True,
            )

        if st.button("Delete plan", key=f"del_plan_{plan['id']}"):
            delete_meal_plan(conn, plan["id"])
            st.rerun()

# --- Recipe lookup ---
st.subheader("Recipe Lookup")
all_recipes = get_all_recipes(conn)
if all_recipes:
    recipe_names = {r["title"]: r["id"] for r in all_recipes}
    selected = st.selectbox("Look up a recipe", ["", *list(recipe_names.keys())])

    if selected:
        history = get_recipe_history(conn, recipe_names[selected])
        if history:
            st.markdown(f"**{selected}** has been planned {len(history)} time(s):")
            for entry in history:
                st.markdown(
                    f"- {entry['plan_name']} ({entry['start_date']}) — {entry['day_label']}"
                )
        else:
            st.info(f"**{selected}** hasn't been used in any plan yet.")
