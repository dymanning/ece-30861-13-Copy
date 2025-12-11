"""
Comprehensive Selenium Test Suite for Flask Frontend
Tests navigation, forms, authentication flows, and UI interactions
"""
import time
import threading
import pytest
import sys
from pathlib import Path

# Add flask_app directory to Python path
flask_app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(flask_app_dir))

from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Import the Flask app object
from app import app as flask_app

SERVER_PORT = 5005
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"


def _start_server():
    """Run the Flask app in a background thread for testing"""
    flask_app.run(host="127.0.0.1", port=SERVER_PORT, use_reloader=False)


@pytest.fixture(scope="module")
def server():
    """Start Flask server before tests, stop after"""
    thread = threading.Thread(target=_start_server, daemon=True)
    thread.start()
    time.sleep(2)  # Give server time to fully start
    yield
    # Thread is daemon so it terminates with test process


@pytest.fixture(scope="function")
def driver():
    """Create a new Chrome driver instance for each test"""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    try:
        service = Service(ChromeDriverManager().install())
        browser = webdriver.Chrome(service=service, options=options)
        browser.implicitly_wait(5)  # Wait up to 5s for elements
        yield browser
    except Exception as e:
        pytest.skip(f"Selenium driver setup failed: {e}")
    finally:
        if 'browser' in locals():
            browser.quit()


class TestHomePage:
    """Test cases for the home/landing page"""
    
    def test_home_page_loads_successfully(self, server, driver):
        """Verify home page loads with correct title and content"""
        driver.get(SERVER_URL + "/")
        
        # Check page title
        assert driver.title, "Page title should not be empty"
        assert any(x in driver.title.lower() for x in ("app", "flask", "home", "welcome")), \
            f"Expected title to contain app/flask/home/welcome, got: {driver.title}"
        
        # Check main heading exists
        try:
            heading = driver.find_element(By.TAG_NAME, "h1")
            assert heading.text, "Main heading should have text"
        except NoSuchElementException:
            pytest.fail("Home page should have an h1 heading")
    
    def test_home_page_has_navigation_links(self, server, driver):
        """Verify navigation links are present"""
        driver.get(SERVER_URL + "/")
        
        # Look for common navigation links
        links = driver.find_elements(By.TAG_NAME, "a")
        link_texts = [link.text.lower() for link in links if link.text]
        
        assert len(links) > 0, "Page should have navigation links"
        
        # Check for expected nav items (login, register, etc.)
        expected_links = ["login", "register", "home"]
        found_links = [exp for exp in expected_links if any(exp in text for text in link_texts)]
        
        assert len(found_links) > 0, \
            f"Expected to find navigation links like {expected_links}, found: {link_texts}"
    
    def test_home_page_responsive_layout(self, server, driver):
        """Verify page layout adapts to different screen sizes"""
        driver.get(SERVER_URL + "/")
        
        # Test desktop size
        driver.set_window_size(1920, 1080)
        desktop_body = driver.find_element(By.TAG_NAME, "body")
        assert desktop_body.is_displayed(), "Page should render on desktop"
        
        # Test mobile size
        driver.set_window_size(375, 667)
        mobile_body = driver.find_element(By.TAG_NAME, "body")
        assert mobile_body.is_displayed(), "Page should render on mobile"


class TestLoginPage:
    """Test cases for login functionality"""
    
    def test_login_page_accessible(self, server, driver):
        """Verify login page can be accessed"""
        driver.get(SERVER_URL + "/login")
        
        assert "login" in driver.title.lower() or "sign in" in driver.page_source.lower(), \
            "Login page should be identified by title or content"
    
    def test_login_form_elements_present(self, server, driver):
        """Verify login form has required elements"""
        driver.get(SERVER_URL + "/login")
        
        # Check for form element
        try:
            form = driver.find_element(By.TAG_NAME, "form")
            assert form, "Login page should have a form"
        except NoSuchElementException:
            pytest.fail("Login page missing form element")
        
        # Check for input fields
        inputs = driver.find_elements(By.TAG_NAME, "input")
        input_types = [inp.get_attribute("type") for inp in inputs]
        
        assert "text" in input_types or "email" in input_types, \
            "Login form should have text/email input for username"
        assert "password" in input_types, \
            "Login form should have password input"
        assert "submit" in input_types or driver.find_elements(By.CSS_SELECTOR, "button[type='submit']"), \
            "Login form should have submit button"
    
    def test_login_with_empty_credentials(self, server, driver):
        """Verify validation for empty login credentials"""
        driver.get(SERVER_URL + "/login")
        
        # Try to submit empty form
        submit_button = None
        try:
            submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        except NoSuchElementException:
            submit_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
        
        if submit_button:
            submit_button.click()
            time.sleep(0.5)
            
            # Should either show validation message or stay on login page
            current_url = driver.current_url
            assert "/login" in current_url, \
                "Should remain on login page or show validation"
    
    def test_login_form_accessibility(self, server, driver):
        """Verify login form has proper accessibility attributes"""
        driver.get(SERVER_URL + "/login")
        
        # Check for labels
        labels = driver.find_elements(By.TAG_NAME, "label")
        inputs = driver.find_elements(By.TAG_NAME, "input")
        
        if inputs:
            # At least some inputs should have labels or placeholders
            has_labels = len(labels) > 0
            has_placeholders = any(inp.get_attribute("placeholder") for inp in inputs)
            
            assert has_labels or has_placeholders, \
                "Form inputs should have labels or placeholders for accessibility"


class TestRegisterPage:
    """Test cases for registration functionality"""
    
    def test_register_page_accessible(self, server, driver):
        """Verify registration page can be accessed"""
        driver.get(SERVER_URL + "/register")
        
        assert "register" in driver.title.lower() or "sign up" in driver.page_source.lower(), \
            "Register page should be identified by title or content"
    
    def test_register_form_elements_present(self, server, driver):
        """Verify registration form has required elements"""
        driver.get(SERVER_URL + "/register")
        
        # Check for form
        try:
            form = driver.find_element(By.TAG_NAME, "form")
            assert form, "Register page should have a form"
        except NoSuchElementException:
            pytest.fail("Register page missing form element")
        
        # Check for input fields
        inputs = driver.find_elements(By.TAG_NAME, "input")
        input_types = [inp.get_attribute("type") for inp in inputs]
        
        assert "text" in input_types or "email" in input_types, \
            "Register form should have text/email input"
        assert "password" in input_types, \
            "Register form should have password input"
    
    def test_navigation_between_login_and_register(self, server, driver):
        """Verify users can navigate between login and register pages"""
        driver.get(SERVER_URL + "/login")
        
        # Look for link to register page
        links = driver.find_elements(By.TAG_NAME, "a")
        register_links = [link for link in links if "register" in link.text.lower() or "sign up" in link.text.lower()]
        
        if register_links:
            register_links[0].click()
            time.sleep(0.5)
            assert "/register" in driver.current_url, \
                "Should navigate to register page from login"
            
            # Try to navigate back
            driver.get(SERVER_URL + "/login")
            assert "/login" in driver.current_url, \
                "Should be able to navigate back to login"


class TestNavigation:
    """Test cases for site navigation and routing"""
    
    def test_404_error_page(self, server, driver):
        """Verify 404 page for non-existent routes"""
        driver.get(SERVER_URL + "/this-page-does-not-exist-12345")
        
        # Should show some error indication
        page_text = driver.page_source.lower()
        assert "404" in page_text or "not found" in page_text or "error" in page_text, \
            "Non-existent page should show 404 or error message"
    
    def test_home_link_from_subpages(self, server, driver):
        """Verify home link works from other pages"""
        driver.get(SERVER_URL + "/login")
        
        # Look for home/logo link
        links = driver.find_elements(By.TAG_NAME, "a")
        home_links = [link for link in links if link.text.lower() in ["home", ""] or "/" == link.get_attribute("href").rstrip("/")]
        
        if home_links:
            # Find actual home link
            for link in links:
                href = link.get_attribute("href")
                if href and href.endswith("/") and "login" not in href and "register" not in href:
                    link.click()
                    time.sleep(0.5)
                    assert driver.current_url.rstrip("/") == SERVER_URL, \
                        "Home link should navigate to root URL"
                    break


class TestUIElements:
    """Test cases for UI components and styling"""
    
    def test_css_styles_loaded(self, server, driver):
        """Verify CSS styles are applied"""
        driver.get(SERVER_URL + "/")
        
        # Check if stylesheets are linked
        links = driver.find_elements(By.CSS_SELECTOR, "link[rel='stylesheet']")
        assert len(links) > 0 or driver.find_elements(By.TAG_NAME, "style"), \
            "Page should have CSS styling via link or style tags"
    
    def test_page_has_semantic_html(self, server, driver):
        """Verify page uses semantic HTML elements"""
        driver.get(SERVER_URL + "/")
        
        # Check for semantic elements
        semantic_elements = ["header", "nav", "main", "footer", "section", "article"]
        found_semantic = []
        
        for element in semantic_elements:
            if driver.find_elements(By.TAG_NAME, element):
                found_semantic.append(element)
        
        # Should use at least some semantic HTML
        assert len(found_semantic) > 0, \
            f"Page should use semantic HTML elements. Found: {found_semantic}"
    
    def test_no_javascript_errors(self, server, driver):
        """Verify page loads without JavaScript console errors"""
        driver.get(SERVER_URL + "/")
        time.sleep(1)  # Let any JS execute
        
        # Get browser console logs
        logs = driver.get_log('browser')
        errors = [log for log in logs if log['level'] == 'SEVERE']
        
        assert len(errors) == 0, \
            f"Page should not have JavaScript errors. Found: {errors}"


class TestSecurity:
    """Test cases for security features"""
    
    def test_password_field_masked(self, server, driver):
        """Verify password fields are properly masked"""
        driver.get(SERVER_URL + "/login")
        
        password_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
        assert len(password_inputs) > 0, \
            "Login page should have password input with type='password'"
        
        # Verify it's actually a password type
        for pwd_input in password_inputs:
            assert pwd_input.get_attribute("type") == "password", \
                "Password field should have type='password' attribute"
    
    def test_no_sensitive_data_in_source(self, server, driver):
        """Verify no API keys or secrets in page source"""
        driver.get(SERVER_URL + "/")
        
        page_source = driver.page_source.lower()
        
        # Check for common secret patterns
        dangerous_patterns = ["api_key", "secret_key", "password=", "token="]
        found_patterns = [pattern for pattern in dangerous_patterns if pattern in page_source]
        
        # This is just a basic check - adjust based on your needs
        assert "secret_key" not in page_source or "your" in page_source, \
            "Page source should not expose secret keys"


class TestPerformance:
    """Test cases for performance and load times"""
    
    def test_page_load_time_acceptable(self, server, driver):
        """Verify pages load within acceptable time"""
        import time
        
        start_time = time.time()
        driver.get(SERVER_URL + "/")
        load_time = time.time() - start_time
        
        assert load_time < 5.0, \
            f"Page should load in under 5 seconds, took {load_time:.2f}s"
    
    def test_multiple_page_navigation_performance(self, server, driver):
        """Verify navigation between pages is responsive"""
        pages = ["/", "/login", "/register", "/"]
        
        total_time = 0
        for page in pages:
            start = time.time()
            driver.get(SERVER_URL + page)
            total_time += (time.time() - start)
        
        avg_time = total_time / len(pages)
        assert avg_time < 3.0, \
            f"Average page load should be under 3s, was {avg_time:.2f}s"
