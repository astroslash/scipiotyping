"""Complete a focused drill in installed Microsoft Edge against a temporary DB."""
from __future__ import annotations

import json
import tempfile
import threading
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from waitress.server import create_server

from scipiotyping import create_app
from scipiotyping.db import get_db
from scipiotyping.lessons import DRILL_TEXTS


def main() -> None:
    with tempfile.TemporaryDirectory() as folder:
        app = create_app({"TESTING": False, "SECRET_KEY": "browser-check", "DATABASE": str(Path(folder) / "browser.db")})
        server = create_server(app, host="127.0.0.1", port=5001, threads=4)
        threading.Thread(target=server.run, daemon=True).start()
        time.sleep(0.5)
        options = webdriver.EdgeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1200,900")
        driver = webdriver.Edge(options=options)
        try:
            driver.get("http://127.0.0.1:5001/practice/drill-home-row?mode=lesson&lesson=home-row")
            passage = driver.find_element(By.ID, "passage")
            assert passage.is_displayed() and passage.text == DRILL_TEXTS["home-row"]
            field = driver.find_element(By.ID, "typing-input")
            field.send_keys("x")
            field.send_keys(Keys.BACKSPACE)
            time.sleep(0.6)  # The server rejects unrealistically sub-half-second attempts.
            for character in DRILL_TEXTS["home-row"]:
                field.send_keys(character)
            WebDriverWait(driver, 10).until(lambda page: page.find_element(By.ID, "results").is_displayed())
            result = driver.find_element(By.ID, "results").text
            assert "Expedition complete" in result and "accuracy: 100%" in result.lower()
            with app.app_context():
                row = get_db().execute("SELECT * FROM attempts").fetchone()
                assert row["completed"] == 1 and row["corrected_errors"] == 1
                assert json.loads(row["error_map"]).get("a") == 1, row["error_map"]
                weak = json.loads(row["key_stats"])
                weak["a"] = {"expected": 20, "matched": 10, "errors": 10}
                get_db().execute("UPDATE attempts SET key_stats=? WHERE id=?", (json.dumps(weak), row["id"]))
                get_db().commit()

            # Personalized path: heatmap recommendation opens and completes a reproducible drill.
            driver.get("http://127.0.0.1:5001/progress")
            assert driver.find_element(By.CSS_SELECTOR, ".key-a, [aria-label^='A,']").is_displayed()
            workshop_links = driver.find_elements(By.LINK_TEXT, "Practice weak keys")
            assert workshop_links and workshop_links[0].is_displayed()
            workshop_links[0].click()
            assert "Weak-Key Workshop" in driver.find_element(By.TAG_NAME, "h1").text
            targeted_text = driver.find_element(By.ID, "passage").text
            targeted_field = driver.find_element(By.ID, "typing-input")
            targeted_field.send_keys(targeted_text[0])
            time.sleep(0.6)
            targeted_field.send_keys(targeted_text[1:])
            WebDriverWait(driver, 10).until(lambda page: page.find_element(By.ID, "results").is_displayed())
            targeted_result = driver.find_element(By.ID, "results").text
            assert "Focus-key results" in targeted_result
            with app.app_context():
                targeted_row = get_db().execute("SELECT * FROM attempts WHERE mode='targeted'").fetchone()
                assert targeted_row["target_text"] == targeted_text and json.loads(targeted_row["focus_keys"])

            # Regression: one omitted interior character must not prevent automatic completion.
            driver.get("http://127.0.0.1:5001/practice/drill-home-row?mode=lesson&lesson=home-row")
            field = driver.find_element(By.ID, "typing-input")
            missing_character = DRILL_TEXTS["home-row"].replace(";", "", 1)
            field.send_keys(missing_character[0])
            time.sleep(0.6)
            field.send_keys(missing_character[1:])
            WebDriverWait(driver, 10).until(lambda page: page.find_element(By.ID, "results").is_displayed())
            imperfect_result = driver.find_element(By.ID, "results").text
            assert "Expedition complete" in imperfect_result and "1 deletions" in imperfect_result
            with app.app_context():
                row = get_db().execute("SELECT * FROM attempts ORDER BY id DESC LIMIT 1").fetchone()
                assert row["completed"] == 1 and row["deletions"] == 1 and row["errors"] == 1

            # Regression: the explicit fallback can score a passage at the 85% threshold.
            driver.get("http://127.0.0.1:5001/practice/drill-home-row?mode=lesson&lesson=home-row")
            field = driver.find_element(By.ID, "typing-input")
            partial = DRILL_TEXTS["home-row"][:round(len(DRILL_TEXTS["home-row"]) * .86)]
            field.send_keys(partial[0])
            time.sleep(0.6)
            field.send_keys(partial[1:])
            finish = driver.find_element(By.ID, "finish-button")
            assert finish.is_displayed()
            finish.click()
            WebDriverWait(driver, 10).until(lambda page: page.find_element(By.ID, "results").is_displayed())
            assert "Expedition complete" in driver.find_element(By.ID, "results").text

            errors = [entry for entry in driver.get_log("browser") if entry["level"] in {"SEVERE", "ERROR"}]
            assert not errors, errors
            driver.find_element(By.CSS_SELECTOR, "[data-display='large']").click()
            driver.find_element(By.CSS_SELECTOR, "[data-display='contrast']").click()
            assert "large-text" in driver.find_element(By.TAG_NAME, "html").get_attribute("class")
            assert "high-contrast" in driver.find_element(By.TAG_NAME, "html").get_attribute("class")
            driver.set_window_size(600, 900)
            driver.get("http://127.0.0.1:5001/lessons")
            assert driver.execute_script("return document.documentElement.scrollWidth <= window.innerWidth")
            print("Microsoft Edge end-to-end typing check passed.")
        finally:
            driver.quit()
            server.close()


if __name__ == "__main__":
    main()
