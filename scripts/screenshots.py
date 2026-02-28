"""Capture screenshots of each page for the GitHub README.

Usage:
    1. Start the app:  streamlit run app.py
    2. Run this script: python scripts/screenshots.py

Screenshots are saved to screenshots/ in the project root.
"""

import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "screenshots"
OUT.mkdir(exist_ok=True)

BASE = "http://localhost:8501"

# Pages to capture: (filename, sidebar_link_text)
PAGES = [
    ("01_recipe_library.png", "Recipe Library"),
    ("02_meal_planner.png", "Meal Planner"),
    ("03_shopping_list.png", "Shopping List"),
    ("04_pantry.png", "Pantry"),
    ("05_add_recipe.png", "Add Recipe"),
]

VIEWPORT = {"width": 1280, "height": 900}


def capture_screenshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport=VIEWPORT,
            color_scheme="dark",
        )
        page = context.new_page()

        # Load the app (default page)
        page.goto(BASE, wait_until="networkidle", timeout=15000)
        time.sleep(2)

        for filename, link_text in PAGES:
            print(f"  {filename} <- {link_text}")
            try:
                # Click sidebar nav link
                link = page.get_by_role("link", name=link_text).first
                link.click()
                page.wait_for_load_state("networkidle")
                time.sleep(2)

                # Hide Streamlit status widget (running spinner)
                page.evaluate("""
                    document.querySelectorAll('[data-testid="stStatusWidget"]')
                        .forEach(el => el.style.display = 'none');
                """)

                path = OUT / filename
                page.screenshot(path=str(path), full_page=False)
            except Exception as e:
                print(f"    SKIP: {e}")

        browser.close()

    print(f"\nDone — {len(list(OUT.glob('*.png')))} screenshots in {OUT}/")


if __name__ == "__main__":
    capture_screenshots()
