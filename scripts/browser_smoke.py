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
            field = driver.find_element(By.ID, "typing-input")
            field.send_keys("x")
            field.send_keys(Keys.BACKSPACE)
            time.sleep(0.6)  # The server rejects unrealistically sub-half-second attempts.
            field.send_keys(DRILL_TEXTS["home-row"])
            WebDriverWait(driver, 10).until(lambda page: page.find_element(By.ID, "results").is_displayed())
            result = driver.find_element(By.ID, "results").text
            assert "Expedition complete" in result and "100% accuracy" in result
            errors = [entry for entry in driver.get_log("browser") if entry["level"] in {"SEVERE", "ERROR"}]
            assert not errors, errors
            with app.app_context():
                row = get_db().execute("SELECT * FROM attempts").fetchone()
                assert row["completed"] == 1 and row["corrected_errors"] == 1
                assert json.loads(row["error_map"]).get("a") == 1
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
