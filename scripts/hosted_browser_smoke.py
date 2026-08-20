"""Exercise hosted access and zoom-safe welcome layouts in Microsoft Edge."""
from __future__ import annotations

import tempfile
import threading
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from waitress.server import create_server

from scipiotyping import create_app


def main_contains(page, text: str) -> bool:
    try:
        return text.casefold() in page.find_element(By.TAG_NAME, "main").text.casefold()
    except WebDriverException:
        return False


def main() -> None:
    with tempfile.TemporaryDirectory() as folder:
        app = create_app({
            "TESTING": True,
            "SECRET_KEY": "hosted-browser-secret-key-at-least-32-characters",
            "DATABASE": str(Path(folder) / "hosted-browser.db"),
            "DATABASE_URL": "",
            "HOSTED_MODE": True,
            "PARENT_PASSWORD": "parent-browser-password",
            "SEED_PROFILE_PINS": {"Kenneth": "1111", "William": "2222", "Alice": "3333"},
        })
        # This temporary QA server uses HTTP; production Vercel always retains Secure cookies over HTTPS.
        app.config["SESSION_COOKIE_SECURE"] = False
        server = create_server(app, host="127.0.0.1", port=5002, threads=4)
        threading.Thread(target=server.run, daemon=True).start()
        time.sleep(0.5)
        options = webdriver.EdgeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1200,900")
        driver = webdriver.Edge(options=options)
        try:
            driver.get("http://127.0.0.1:5002/")
            WebDriverWait(driver, 10).until(lambda page: page.current_url.endswith("/profiles"))
            page = driver.find_element(By.TAG_NAME, "main").text
            assert "welcome to scipiotyping" in page.casefold()
            assert all(name in page for name in ("Kenneth", "William", "Alice"))

            for zoom, width in ((1, 1200), (1.25, 960), (1.5, 800), (2, 600)):
                driver.set_window_size(width, 900)
                assert driver.execute_script(
                    "return document.documentElement.scrollWidth <= window.innerWidth + 1"
                ), f"Profiles welcome overflowed at {zoom * 100:.0f}% zoom"
            driver.set_window_size(1200, 900)

            william_form = driver.find_element(By.CSS_SELECTOR, "form[action$='/profiles/2/select']")
            william_form.find_element(By.NAME, "pin").send_keys("2222")
            william_form.find_element(By.TAG_NAME, "button").click()
            WebDriverWait(driver, 10).until(lambda page: main_contains(page, "Salve, William"))

            for zoom, width in ((1, 1200), (1.25, 960), (1.5, 800), (2, 600)):
                driver.set_window_size(width, 900)
                title = driver.find_element(By.CSS_SELECTOR, ".hero-title")
                assert title.value_of_css_property("word-break") == "normal"
                assert driver.execute_script(
                    "const r=arguments[0].getBoundingClientRect();"
                    "return r.left >= 0 && r.right <= window.innerWidth + 1 && "
                    "arguments[0].scrollWidth <= arguments[0].clientWidth + 1 && "
                    "document.documentElement.scrollWidth <= window.innerWidth + 1", title
                ), f"Home welcome title clipped at {zoom * 100:.0f}% zoom"
            driver.set_window_size(1200, 900)

            driver.find_element(By.LINK_TEXT, "Parent").click()
            assert "Parent area locked" in driver.find_element(By.TAG_NAME, "h1").text
            driver.find_element(By.NAME, "password").send_keys("parent-browser-password")
            driver.find_element(By.CSS_SELECTOR, "form[action$='/parent/unlock'] button").click()
            WebDriverWait(driver, 10).until(lambda page: main_contains(page, "Parent dashboard"))
            dashboard = driver.find_element(By.TAG_NAME, "main").text.lower()
            assert "private hosted database" in dashboard and "new learner pin" in dashboard
            assert driver.execute_script("return document.documentElement.scrollWidth <= window.innerWidth")
            errors = [entry for entry in driver.get_log("browser") if entry["level"] in {"SEVERE", "ERROR"}]
            assert not errors, errors
            print("Microsoft Edge hosted-access check passed.")
        finally:
            driver.quit()
            server.close()


if __name__ == "__main__":
    main()
