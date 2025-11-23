import time
import threading
import pytest

from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# Import the Flask app object
from phase2.flask_app.app import app as flask_app

SERVER_PORT = 5005
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"


def _start_server():
    # Run the Flask app in a background thread for testing
    flask_app.run(host="127.0.0.1", port=SERVER_PORT, use_reloader=False)


@pytest.fixture(scope="module")
def server():
    thread = threading.Thread(target=_start_server, daemon=True)
    thread.start()
    time.sleep(1)  # give server a moment to start
    yield
    # No explicit teardown; thread is daemon so it ends with the process


def test_home_page_loads(server):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        pytest.skip(f"Selenium driver setup failed: {e}")

    try:
        driver.get(SERVER_URL + "/")
        time.sleep(0.5)
        assert any(x in driver.title for x in ("App", "Flask", "Home"))
    finally:
        driver.quit()
